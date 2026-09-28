#!/usr/bin/env npx tsx
/**
 * 从本地书单目录增量导入藏书到 src/content/books/。
 *
 * 特性：
 * - **增量且幂等**：已存在 index.md 的书目目录一个字节都不动，重跑无副作用。
 * - **默认演练**：不带 --apply 时只打印计划，不写盘。
 * - 封面三级解析：EPUB 内封面 → 设备封面缓存 → 生成占位图（占位图标 coverSource）。
 * - 作者三级回退：书单 JSON 元数据 → EPUB dc:creator → 人工 overrides。
 * - 简介与作者的人工部分集中在 scripts/book-library-overrides.json，便于逐条审校。
 *
 * 用法:
 *   npx tsx scripts/import-book-library.ts              # 演练
 *   npx tsx scripts/import-book-library.ts --apply      # 执行
 *   npx tsx scripts/import-book-library.ts --only 双城记 # 只处理一本
 *
 * 依赖：unzip（系统命令）、sharp、pinyin-pro（均为项目已有依赖）。
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { pinyin } from "pinyin-pro";
import sharp from "sharp";

const PROJECT = path.resolve(import.meta.dirname, "..");
const BOOKS_DIR = path.join(PROJECT, "src/content/books");
const OVERRIDES_PATH = path.join(
	PROJECT,
	"scripts/book-library-overrides.json",
);

/** 源目录分类 → shelf 枚举值（与 src/types/book.ts 的 BOOK_SHELF_VALUES 对应） */
const SHELF_BY_CAT: Record<string, string> = {
	传记: "biography",
	工具书: "reference",
	经济: "economics",
	科幻: "sci-fi",
	科学: "science",
	历史: "history",
	逻辑: "logic",
	社会: "society",
	文学: "literature",
	小说: "fiction",
	心理: "psychology",
	艺术: "art",
	哲学: "philosophy",
	政治: "politics",
};

const BOOK_EXT = new Set([".epub", ".pdf", ".mobi"]);
const COVER_WIDTH = 480;

interface Overrides {
	/** 源书名 → 已存在的 slug：源目录取名与已有条目不同时用它消解重复 */
	aliases: Record<string, string>;
	/** 源书名 → 作者数组 */
	authors: Record<string, string[]>;
	/** 源书名 → 自撰内容概述 */
	descriptions: Record<string, string>;
	/** 源书名 → 状态（默认 wishlist） */
	statuses?: Record<string, "wishlist" | "reading" | "read">;
}

interface SourceBook {
	cat: string;
	stem: string;
	filePath: string;
	shelf: string;
}

interface Harvested {
	title: string;
	creators: string[];
	description: string;
	coverEntry: string | null;
}

// ───────────────────────── 工具 ─────────────────────────

const normTitle = (s: string): string =>
	s
		.replace(/[（(][^（()）]*[）)]/g, "")
		.replace(/[\s　·・:：,，。、\-—_!！?？'"“”‘’《》()[\]【】]+/g, "")
		.toLowerCase();

function slugify(title: string): string {
	const parts: string[] = [];
	let buffer = "";
	for (const ch of title) {
		if (/[一-鿿]/.test(ch)) {
			if (buffer) {
				parts.push(buffer);
				buffer = "";
			}
			// v:true 必须保留，否则「女」的 ü 会被吞成 n
			parts.push(pinyin(ch, { toneType: "none", type: "array" })[0] as string);
		} else {
			buffer += ch;
		}
	}
	if (buffer) parts.push(buffer);
	return parts
		.join("-")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-+|-+$/g, "");
}

function unzip(args: string[]): string | null {
	try {
		return execFileSync("unzip", args, {
			encoding: "utf-8",
			maxBuffer: 64 * 1024 * 1024,
		});
	} catch {
		return null;
	}
}

function unzipBuffer(epub: string, entry: string): Buffer | null {
	try {
		return execFileSync("unzip", ["-p", epub, entry], {
			maxBuffer: 64 * 1024 * 1024,
		});
	} catch {
		return null;
	}
}

const stripTags = (s: string): string =>
	s
		.replace(/<[^>]+>/g, "")
		.replace(/&amp;/g, "&")
		.replace(/&lt;/g, "<")
		.replace(/&gt;/g, ">")
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'")
		.trim();

/** 把 dc:creator 的常见噪声（国别、著译、下载站）清洗成干净姓名列表 */
function cleanCreators(raw: string): string[] {
	return raw
		.split(/[;,；、]/)
		.map((s) =>
			s
				.replace(/^[\s[【（(]*[^一-鿿A-Za-z]*[\s\]】）)]*/u, "")
				.replace(/[\s　]*(著|译|编|主编|等)\s*$/u, "")
				.replace(/\((?:z-library|1lib|z-lib)[^)]*\)/gi, "")
				.trim(),
		)
		.filter(
			(s) =>
				s.length > 1 &&
				!/^\d+$/.test(s) &&
				!/chenjin5|knowledge house|z-library|1lib/i.test(s),
		);
}

// ───────────────────── EPUB 采集 ─────────────────────

function harvestEpub(epub: string): Harvested | null {
	const listing = unzip(["-Z1", epub]);
	if (!listing) return null;
	const entries = listing
		.split("\n")
		.map((s) => s.trim())
		.filter(Boolean);
	const opfEntry = entries.find((e) => e.toLowerCase().endsWith(".opf"));
	if (!opfEntry) return null;

	const opfRaw = unzip(["-p", epub, opfEntry]);
	if (!opfRaw) return null;
	const opf = opfRaw.toString("utf-8");

	const pick = (tag: string): string => {
		const m = opf.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "i"));
		return m ? stripTags(m[1]) : "";
	};
	const title = pick("dc:title");
	const creators = cleanCreators(pick("dc:creator"));
	const description = pick("dc:description");

	const opfDir = path.posix.dirname(opfEntry);
	const resolveHref = (href: string): string =>
		href.startsWith("/")
			? href.slice(1)
			: path.posix.normalize(path.posix.join(opfDir, href));

	// 三级：properties="cover-image" → <meta name="cover"> → 文件名含 cover
	let coverEntry: string | null = null;
	const propsMatch =
		opf.match(/<item[^>]*properties="[^"]*cover-image[^"]*"[^>]*>/i) ??
		opf.match(/<item[^>]*href="([^"]+)"[^>]*properties="[^"]*cover-image/i);
	if (propsMatch) {
		const href = propsMatch[1] ?? propsMatch[0].match(/href="([^"]+)"/i)?.[1];
		if (href) coverEntry = resolveHref(href);
	}
	if (!coverEntry) {
		const metaId = opf.match(
			/<meta[^>]*name="cover"[^>]*content="([^"]+)"/i,
		)?.[1];
		if (metaId) {
			const itemRe = new RegExp(
				`<item[^>]*(?:id="${metaId}"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*id="${metaId}")`,
				"i",
			);
			const m = opf.match(itemRe);
			const href = m?.[1] ?? m?.[2];
			if (href) coverEntry = resolveHref(href);
		}
	}
	if (!coverEntry) {
		const candidate = entries.find(
			(e) => /\.(jpe?g|png)$/i.test(e) && /cover/i.test(path.posix.basename(e)),
		);
		if (candidate) coverEntry = candidate;
	}
	if (coverEntry && !entries.includes(coverEntry)) {
		const target = path.posix.basename(coverEntry);
		const alt = entries.find((e) => path.posix.basename(e) === target);
		coverEntry = alt ?? null;
	}

	return { title, creators, description, coverEntry };
}

// ───────────────────── 封面处理 ─────────────────────

async function toCoverWebp(input: Uint8Array): Promise<Buffer | null> {
	try {
		return await sharp(input)
			.resize({ width: COVER_WIDTH, withoutEnlargement: true })
			.webp({ quality: 82 })
			.toBuffer();
	} catch {
		return null;
	}
}

/** 确定性占位封面：书名 hash 决定色相，避免每次重跑变色 */
async function makePlaceholder(title: string): Promise<Buffer> {
	let hash = 0;
	for (const ch of title) hash = (hash * 31 + (ch.codePointAt(0) ?? 0)) % 360;
	const hue = hash;
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${COVER_WIDTH}" height="720">
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="hsl(${hue},38%,42%)"/>
    <stop offset="100%" stop-color="hsl(${(hue + 40) % 360},42%,26%)"/>
  </linearGradient></defs>
  <rect width="100%" height="100%" fill="url(#g)"/>
  <text x="50%" y="50%" fill="rgba(255,255,255,.92)" font-size="34"
        font-family="sans-serif" text-anchor="middle" dominant-baseline="middle">
    ${title.replace(/[<>&]/g, "")}
  </text>
</svg>`;
	return sharp(new Uint8Array(Buffer.from(svg)))
		.webp({ quality: 82 })
		.toBuffer();
}

// ───────────────────── 数据源 ─────────────────────

function loadOverrides(): Overrides {
	if (!fs.existsSync(OVERRIDES_PATH)) {
		return { aliases: {}, authors: {}, descriptions: {} };
	}
	const raw = JSON.parse(fs.readFileSync(OVERRIDES_PATH, "utf-8"));
	return {
		aliases: raw.aliases ?? {},
		authors: raw.authors ?? {},
		descriptions: raw.descriptions ?? {},
		statuses: raw.statuses ?? {},
	};
}

/** 书单目录里的 author 字段（下载时留存的干净元数据） */
function loadMetadataAuthors(source: string): Map<string, string[]> {
	const out = new Map<string, string[]>();
	const toolDir = path.join(source, "_工具");
	if (!fs.existsSync(toolDir)) return out;
	for (const f of fs.readdirSync(toolDir)) {
		if (!/^books.*\.json$|^phase\d+_books\.json$/.test(f)) continue;
		try {
			const data = JSON.parse(fs.readFileSync(path.join(toolDir, f), "utf-8"));
			const items = Array.isArray(data) ? data : Object.values(data);
			for (const it of items as Array<Record<string, string>>) {
				if (it?.title && it?.author) {
					out.set(normTitle(it.title), cleanCreators(it.author));
				}
			}
		} catch {
			// 元数据文件可选，解析失败不阻断
		}
	}
	return out;
}

function collectSourceBooks(source: string): SourceBook[] {
	const books: SourceBook[] = [];
	for (const cat of Object.keys(SHELF_BY_CAT)) {
		const dir = path.join(source, cat);
		if (!fs.existsSync(dir)) continue;
		for (const file of fs.readdirSync(dir)) {
			const ext = path.extname(file).toLowerCase();
			if (!BOOK_EXT.has(ext)) continue;
			books.push({
				cat,
				stem: path.basename(file, ext),
				filePath: path.join(dir, file),
				shelf: SHELF_BY_CAT[cat],
			});
		}
	}
	return books.sort((a, b) => a.stem.localeCompare(b.stem, "zh-CN"));
}

/** 已有条目：归一化书名 → slug（用于跳过与别名解析） */
function loadExisting(): Map<string, string> {
	const out = new Map<string, string>();
	if (!fs.existsSync(BOOKS_DIR)) return out;
	for (const slug of fs.readdirSync(BOOKS_DIR)) {
		const idx = path.join(BOOKS_DIR, slug, "index.md");
		if (!fs.existsSync(idx)) continue;
		const txt = fs.readFileSync(idx, "utf-8");
		const m = txt.match(/^title:\s*"?(.+?)"?\s*$/m);
		if (m) out.set(normTitle(m[1]), slug);
	}
	return out;
}

// ───────────────────── 输出 ─────────────────────

/** JSON 双引号串本身就是合法的 YAML 双引号标量，最省心的转义方式 */
const q = (s: string): string => JSON.stringify(s);

function emitIndexMd(fields: {
	title: string;
	authors: string[];
	description: string;
	status: string;
	shelf: string;
	coverSource: string;
}): string {
	const lines = [
		"---",
		`title: ${q(fields.title)}`,
		`authors: [${fields.authors.map(q).join(", ")}]`,
		`description: ${q(fields.description)}`,
		`status: ${q(fields.status)}`,
		`shelf: ${q(fields.shelf)}`,
		"topics: []",
		'cover: "./cover.webp"',
		`coverSource: ${q(fields.coverSource)}`,
		"---",
		"",
	];
	// 仅校验字段行本身：值里的换行已被 JSON.stringify 转义成字面量 \n，
	// 若某字段行退化成一个裸 --- 就会截断 obsidian-bridge.py 的 split("---", 2)
	const fieldLines = lines.slice(1, -2); // 去掉首行 --- 与末尾的 --- /空行
	if (fieldLines.some((line) => line.trim() === "---")) {
		throw new Error("frontmatter 字段行出现裸 ---，会破坏解析");
	}
	return lines.join("\n");
}

// ───────────────────── 设备封面兜底 ─────────────────────

const DEVICE_COVER_DIR = path.join(PROJECT, ".local/device-covers");
const DEVICE_FRONT_ROOT = "/sdcard/hwsys/FrontImageRoot";

/**
 * 从电纸书拉取封面缓存，按 slug 存为 .local/device-covers/<slug>.jpg。
 * PDF/MOBI 没有内嵌封面时靠它兜底；设备缓存实际是 192×320 的 JPEG（后缀却是 .png）。
 */
function fetchDeviceCovers(
	books: SourceBook[],
	only?: string | null,
): { pulled: number; missing: string[] } {
	fs.mkdirSync(DEVICE_COVER_DIR, { recursive: true });
	let listing: string;
	try {
		listing = execFileSync("adb", ["shell", "ls", DEVICE_FRONT_ROOT], {
			encoding: "utf-8",
			maxBuffer: 16 * 1024 * 1024,
		});
	} catch {
		throw new Error("无法读取设备封面目录（adb 是否已连接？）");
	}
	const covers = listing
		.split("\n")
		.map((s) => s.trim())
		.filter(Boolean)
		.map((name) => ({ name, norm: normTitle(name) }));

	let pulled = 0;
	const missing: string[] = [];
	for (const book of books) {
		if (only && !book.stem.includes(only)) continue;
		const slug = slugify(book.stem);
		const target = path.join(DEVICE_COVER_DIR, `${slug}.jpg`);
		if (fs.existsSync(target)) continue;
		const key = normTitle(book.stem);
		const hit =
			covers.find((c) => c.norm.includes(key)) ??
			covers.find((c) => key.length > 3 && c.norm.endsWith(key));
		if (!hit) {
			missing.push(book.stem);
			continue;
		}
		execFileSync("adb", ["pull", `${DEVICE_FRONT_ROOT}/${hit.name}`, target]);
		pulled++;
	}
	return { pulled, missing };
}

// ───────────────────── 主流程 ─────────────────────

async function main(): Promise<void> {
	const args = process.argv.slice(2);
	const apply = args.includes("--apply");
	const onlyIdx = args.indexOf("--only");
	const only = onlyIdx >= 0 ? args[onlyIdx + 1] : null;
	const srcIdx = args.indexOf("--source");
	const source =
		srcIdx >= 0
			? args[srcIdx + 1]
			: path.join(process.env.HOME ?? "", "下载/书单");

	if (!fs.existsSync(source)) {
		console.error(`✗ 源目录不存在: ${source}`);
		process.exit(1);
	}

	const overrides = loadOverrides();
	const metaAuthors = loadMetadataAuthors(source);
	const existing = loadExisting();
	const books = collectSourceBooks(source);

	if (args.includes("--fetch-covers")) {
		const { pulled, missing } = fetchDeviceCovers(books, only);
		console.log(`\n拉取设备封面 ${pulled} 张 → ${DEVICE_COVER_DIR}`);
		if (missing.length) {
			console.log(`设备上未匹配到封面 ${missing.length} 本（将用生成占位图）:`);
			for (const m of missing) console.log(`   ${m}`);
		}
		return;
	}

	const created: string[] = [];
	const kept: Array<{ stem: string; slug: string; why: string }> = [];
	const skipped: Array<{ stem: string; why: string }> = [];
	const collisions = new Map<string, string[]>();

	for (const book of books) {
		if (only && !book.stem.includes(only)) continue;
		const norm = normTitle(book.stem);

		// 1) 别名命中已有条目 → 跳过
		const aliasSlug = overrides.aliases[book.stem];
		if (aliasSlug) {
			kept.push({ stem: book.stem, slug: aliasSlug, why: "alias" });
			continue;
		}
		// 2) 书名归一化命中已有条目 → 跳过
		const exact = existing.get(norm);
		if (exact) {
			kept.push({ stem: book.stem, slug: exact, why: "exists" });
			continue;
		}
		// 3) 模糊命中（源名与已有书名互为子串）→ 跳过，避免重复导入
		const fuzzy = [...existing.entries()].find(
			([k]) => k.length > 1 && (k.includes(norm) || norm.includes(k)),
		);
		if (fuzzy) {
			kept.push({ stem: book.stem, slug: fuzzy[1], why: "fuzzy" });
			continue;
		}

		const slug = slugify(book.stem);
		collisions.set(slug, [...(collisions.get(slug) ?? []), book.stem]);

		const description = overrides.descriptions[book.stem];
		if (!description) {
			skipped.push({ stem: book.stem, why: "缺自撰简介" });
			continue;
		}

		let authors = overrides.authors[book.stem] ?? [];
		let harvested: Harvested | null = null;
		if (book.filePath.endsWith(".epub")) {
			harvested = harvestEpub(book.filePath);
			if (authors.length === 0 && harvested?.creators.length) {
				authors = harvested.creators;
			}
		}
		if (authors.length === 0) authors = metaAuthors.get(norm) ?? [];
		if (authors.length === 0) {
			skipped.push({ stem: book.stem, why: "缺作者" });
			continue;
		}

		// 封面
		let coverBuf: Buffer | null = null;
		let coverSource = "placeholder";
		if (book.filePath.endsWith(".epub") && harvested?.coverEntry) {
			const raw = unzipBuffer(book.filePath, harvested.coverEntry);
			if (raw) {
				coverBuf = await toCoverWebp(raw);
				if (coverBuf) coverSource = "epub";
			}
		}
		if (!coverBuf) {
			const deviceCover = path.join(
				PROJECT,
				".local/device-covers",
				`${slug}.jpg`,
			);
			if (fs.existsSync(deviceCover)) {
				coverBuf = await toCoverWebp(fs.readFileSync(deviceCover));
				if (coverBuf) coverSource = "device";
			}
		}
		if (!coverBuf) {
			coverBuf = await makePlaceholder(book.stem);
		}

		const dir = path.join(BOOKS_DIR, slug);
		const md = emitIndexMd({
			title: book.stem,
			authors,
			description,
			status: overrides.statuses?.[book.stem] ?? "wishlist",
			shelf: book.shelf,
			coverSource,
		});

		if (apply) {
			fs.mkdirSync(dir, { recursive: true });
			fs.writeFileSync(path.join(dir, "index.md"), md, "utf-8");
			fs.writeFileSync(path.join(dir, "cover.webp"), coverBuf);
			const size = fs.statSync(path.join(dir, "cover.webp")).size;
			if (size < 1024) throw new Error(`${slug}: 封面文件异常小 (${size}B)`);
		}
		created.push(
			`${slug}${coverSource === "placeholder" ? " [占位封面]" : ""}`,
		);
	}

	const dupes = [...collisions.entries()].filter(([, v]) => v.length > 1);

	console.log(`\n源目录: ${source}`);
	console.log(`模式: ${apply ? "apply（已写盘）" : "dry-run（未写盘）"}\n`);
	console.log(`  新建:   ${created.length}`);
	console.log(`  已存在: ${kept.length}`);
	console.log(`  跳过:   ${skipped.length}`);
	if (dupes.length) console.log(`  ⚠ slug 碰撞: ${dupes.length}`);

	if (kept.length) {
		console.log("\n已存在（沿用原条目）:");
		for (const k of kept) console.log(`   [${k.why}] ${k.stem} → ${k.slug}`);
	}
	if (skipped.length) {
		console.log("\n跳过（数据未备齐）:");
		for (const s of skipped) console.log(`   ${s.stem} — ${s.why}`);
	}
	if (dupes.length) {
		console.log("\n⚠ slug 碰撞（需在 overrides 中消解）:");
		for (const [slug, stems] of dupes)
			console.log(`   ${slug}: ${stems.join(" / ")}`);
	}
	if (created.length) {
		console.log("\n新建清单:");
		for (const c of created) console.log(`   + ${c}`);
	}
	if (!apply) console.log("\n（演练模式，加 --apply 执行）\n");
}

main().catch((error) => {
	console.error(`✗ ${error instanceof Error ? error.message : error}`);
	process.exit(1);
});
