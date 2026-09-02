/**
 * generate-icons-data.ts
 *
 * 扫描 src 下所有 UI 源码中引用的 `lucide:<name>` 图标，
 * 从 @iconify-json/lucide 中抽取对应的 SVG body，生成
 * src/constants/icons-data.json（供 Icon.svelte 离线渲染，无网络请求）。
 *
 * 用法：pnpm icons（或随 pnpm build 自动执行）
 */

import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const SRC_ROOT = join(process.cwd(), "src");
const SKIP_DIRS = new Set(["content"]);
const SKIP_FILE = "icons-data.json";
const OUT_FILE = join(SRC_ROOT, "constants", "icons-data.json");
const LUCIDE_JSON = join(
	process.cwd(),
	"node_modules",
	"@iconify-json",
	"lucide",
	"icons.json",
);

const lucide = JSON.parse(readFileSync(LUCIDE_JSON, "utf-8")) as {
	icons: Record<string, { body: string }>;
};
const iconNameRe = /["'`]lucide:([a-z0-9-]+)["'`]/g;

function walk(dir: string): string[] {
	const out: string[] = [];
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		if (entry.isDirectory()) {
			if (!SKIP_DIRS.has(entry.name)) out.push(...walk(join(dir, entry.name)));
		} else if (entry.isFile() && entry.name !== SKIP_FILE) {
			out.push(join(dir, entry.name));
		}
	}
	return out;
}

const used = new Set<string>();
for (const file of walk(SRC_ROOT)) {
	const text = readFileSync(file, "utf-8");
	for (const m of text.matchAll(iconNameRe)) used.add(m[1]);
}

const missing: string[] = [];
const icons: Record<string, { body: string }> = {};
for (const name of [...used].sort()) {
	const data = lucide.icons[name];
	if (data) icons[name] = { body: data.body };
	else missing.push(name);
}

if (missing.length > 0) {
	console.error(`[icons] 在 Lucide 集合中找不到：${missing.join(", ")}`);
	process.exit(1);
}

const payload = {
	lucide: { prefix: "lucide", icons },
};

writeFileSync(OUT_FILE, `${JSON.stringify(payload, null, "\t")}\n`, "utf-8");
console.log(
	`[icons] 已生成 ${OUT_FILE}（${Object.keys(icons).length} 个 Lucide 图标）`,
);
