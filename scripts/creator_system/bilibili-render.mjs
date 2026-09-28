#!/usr/bin/env node
import { createHash } from "node:crypto";
import {
	lstat,
	mkdir,
	readFile,
	rename,
	unlink,
	writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createMarkdownProcessor } from "@astrojs/markdown-remark";
import { toString as nodeText } from "mdast-util-to-string";
import sanitizeHtml from "sanitize-html";
import sharp from "sharp";
import { prepareArticle } from "./article-source.mjs";

const MARKER = ".creator-bilibili.json";
const PROJECT = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	"../..",
);
const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_IMAGE_PIXELS = 40_000_000;
const hash = (value) => createHash("sha256").update(value).digest("hex");
const escapeHtml = (value) =>
	String(value)
		.replaceAll("&", "&amp;")
		.replaceAll("<", "&lt;")
		.replaceAll(">", "&gt;")
		.replaceAll('"', "&quot;");
const json = (value) => `${JSON.stringify(value, null, 2)}\n`;
const safeScriptValue = (value) =>
	JSON.stringify(value).replaceAll("<", "\\u003c");

async function noSymlinks(filename) {
	let cursor = path.resolve(filename);
	while (true) {
		try {
			if ((await lstat(cursor)).isSymbolicLink())
				throw new Error(`拒绝符号链接路径：${path.basename(cursor)}`);
		} catch (error) {
			if (error.code !== "ENOENT") throw error;
		}
		const parent = path.dirname(cursor);
		if (parent === cursor) return;
		cursor = parent;
	}
}

function publicText(value, field) {
	if (
		typeof value !== "string" ||
		/\[\[|%%|(?:file|obsidian):\/\/|\/(?:home|Users|root|tmp|mnt|media|Volumes)\/|\b[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/]/i.test(
			value,
		)
	)
		throw new Error(`${field}必须是可公开文字，不能含私链或本地路径`);
	return value;
}

async function imagesFrom(manifestPath) {
	if (!manifestPath) return { images: [], signature: null };
	await noSymlinks(manifestPath);
	const raw = await readFile(manifestPath);
	const manifest = JSON.parse(raw.toString("utf8"));
	if (
		manifest.schema !== 1 ||
		!Array.isArray(manifest.images) ||
		manifest.images.length > 30
	)
		throw new Error(
			"图片manifest需要schema:1和images数组，最多30张（本地处理上限）",
		);
	const images = [];
	const ids = new Set();
	for (const [index, item] of manifest.images.entries()) {
		if (
			!item ||
			typeof item.id !== "string" ||
			!/^[a-z0-9][a-z0-9_-]{0,60}$/i.test(item.id) ||
			ids.has(item.id)
		)
			throw new Error("图片id必须唯一且仅含字母、数字、下划线或连字符");
		ids.add(item.id);
		if (
			typeof item.path !== "string" ||
			!item.path ||
			path.isAbsolute(item.path) ||
			item.path.split(/[\\/]/).includes("..") ||
			item.path.includes("\\")
		)
			throw new Error("图片path必须相对manifest目录且不能跳转上级目录");
		if (!/\.(?:png|jpe?g|webp)$/i.test(item.path))
			throw new Error("图片只支持PNG、JPEG、WebP");
		const caption = publicText(item.caption, "caption");
		if (!caption.trim()) throw new Error("图片需要非空caption");
		const afterHeading =
			item.after_heading === undefined
				? null
				: publicText(item.after_heading, "after_heading");
		if (afterHeading !== null && !afterHeading.trim())
			throw new Error("after_heading不能是空字符串");
		const source = item.source ?? "provided";
		if (!["provided", "local_catalog"].includes(source))
			throw new Error("source只能是provided或local_catalog");
		const filename = path.resolve(path.dirname(manifestPath), item.path);
		await noSymlinks(filename);
		const stat = await lstat(filename);
		if (!stat.isFile() || stat.size > MAX_IMAGE_BYTES)
			throw new Error("图片必须为普通文件且不超过20MiB（本地处理上限）");
		const bytes = await readFile(filename);
		if (bytes.length > MAX_IMAGE_BYTES)
			throw new Error("读取时图片超过本地体积上限");
		const image = sharp(bytes, {
			limitInputPixels: MAX_IMAGE_PIXELS,
			animated: false,
		});
		const metadata = await image.metadata();
		if (
			!["png", "jpeg", "webp"].includes(metadata.format) ||
			(metadata.pages ?? 1) > 1
		)
			throw new Error("只接受静态PNG、JPEG、WebP，不接受动画或其他格式");
		const extension = metadata.format === "jpeg" ? "jpg" : "png";
		const converted =
			extension === "jpg"
				? await image.rotate().jpeg({ quality: 92 }).toBuffer()
				: await image.rotate().png().toBuffer();
		if (converted.length > MAX_IMAGE_BYTES)
			throw new Error("图片转换后超过20MiB本地上限，请先缩小素材");
		images.push({
			id: item.id,
			caption,
			after_heading: afterHeading,
			source,
			file: `images/${String(index + 1).padStart(2, "0")}-${item.id}.${extension}`,
			sha256: hash(converted),
			source_sha256: hash(bytes),
			source_path: filename,
			bytes: converted,
			token: `CREATORIMAGE${index}${hash(converted).slice(0, 16)}`,
		});
	}
	return {
		images,
		signature: hash(
			Buffer.concat([
				raw,
				Buffer.from(images.map((image) => image.source_sha256).join("\n")),
			]),
		),
	};
}

function textOf(node, definitions) {
	const children = () =>
		(node.children || []).map((child) => textOf(child, definitions)).join("");
	if (["text", "inlineCode", "code"].includes(node.type)) return node.value;
	if (node.type === "definition") return "";
	if (node.type === "link") return `${children()}（${node.url}）`;
	if (node.type === "linkReference")
		return `${children()}（${definitions.get(node.identifier)}）`;
	if (node.type === "listItem") return `• ${children().trim()}\n`;
	if (["paragraph", "heading", "blockquote", "list"].includes(node.type))
		return `${children().trim()}\n\n`;
	if (node.type === "break") return "\n";
	return children();
}

async function adapt(markdown, images) {
	let title;
	let plain;
	const adaptTree = () => (tree) => {
		const titles = tree.children.filter(
			(node) => node.type === "heading" && node.depth === 1,
		);
		if (titles.length !== 1)
			throw new Error("稿件需要且只能有一个一级标题，标题将与正文分离");
		title = nodeText(titles[0]).trim();
		if (!title) throw new Error("文章标题不能为空");
		tree.children = tree.children.filter((node) => node !== titles[0]);
		const definitions = new Map(
			tree.children
				.filter((node) => node.type === "definition")
				.map((node) => [node.identifier, node.url]),
		);
		const headingCounts = new Map();
		function count(node) {
			if (node.type === "heading")
				headingCounts.set(
					nodeText(node),
					(headingCounts.get(nodeText(node)) ?? 0) + 1,
				);
			for (const child of node.children || []) count(child);
		}
		count(tree);
		for (const image of images)
			if (
				image.after_heading !== null &&
				headingCounts.get(image.after_heading) !== 1
			)
				throw new Error(
					`图片插入标题必须在正文唯一存在：${image.after_heading}`,
				);
		function normalize(node) {
			if (node.type === "heading")
				node.depth = Math.min(Math.max(node.depth, 2), 3);
			if (node.type === "inlineCode")
				return { type: "text", value: node.value };
			if (node.type === "code")
				return {
					type: "blockquote",
					children: node.value.split("\n").map((line) => ({
						type: "paragraph",
						children: [{ type: "text", value: line || " " }],
					})),
				};
			if (node.type === "table") {
				const [header, ...rows] = node.children;
				return rows.map((row) => ({
					type: "paragraph",
					children: row.children.flatMap((cell, index) => [
						{
							type: "strong",
							children: [
								{
									type: "text",
									value: `${nodeText(header.children[index]) || `列${index + 1}`}：`,
								},
							],
						},
						...cell.children,
						{
							type: "text",
							value: index === row.children.length - 1 ? "" : "； ",
						},
					]),
				}));
			}
			if (
				["delete", "footnoteDefinition", "footnoteReference"].includes(
					node.type,
				) ||
				typeof node.checked === "boolean"
			)
				throw new Error(
					"请将删除线、脚注或任务清单改为明确的普通文字/公开来源链接后导出，避免平台改变含义",
				);
			if (node.type === "thematicBreak")
				return { type: "paragraph", children: [{ type: "text", value: "——" }] };
			if (node.children)
				node.children = node.children.flatMap((child) => {
					const normalized = normalize(child);
					const additions =
						child.type === "heading"
							? images
									.filter((image) => image.after_heading === nodeText(child))
									.map((image) => ({
										type: "paragraph",
										children: [{ type: "text", value: image.token }],
									}))
							: [];
					return [
						...(Array.isArray(normalized) ? normalized : [normalized]),
						...additions,
					];
				});
			return node;
		}
		normalize(tree);
		for (const image of images.filter((entry) => entry.after_heading === null))
			tree.children.push({
				type: "paragraph",
				children: [{ type: "text", value: image.token }],
			});
		plain = textOf(tree, definitions).trim();
	};
	const processor = await createMarkdownProcessor({
		syntaxHighlight: false,
		remarkPlugins: [adaptTree],
	});
	const result = await processor.render(markdown);
	let clipboard = sanitizeHtml(result.code, {
		allowedTags: [
			"h2",
			"h3",
			"p",
			"strong",
			"em",
			"blockquote",
			"ul",
			"ol",
			"li",
			"a",
			"br",
		],
		allowedAttributes: { a: ["href", "title"] },
		allowedSchemes: ["https"],
		allowProtocolRelative: false,
	});
	let preview = clipboard;
	for (const [index, image] of images.entries()) {
		const placeholder = `【插图 ${index + 1}：${image.caption}】`;
		const token = `<p>${image.token}</p>`;
		if (!clipboard.includes(token))
			throw new Error("无法唯一定位图片占位，请检查稿件结构");
		clipboard = clipboard.replace(token, `<p>${escapeHtml(placeholder)}</p>`);
		preview = preview.replace(
			token,
			`<figure><img src="${image.file}" alt="${escapeHtml(image.caption)}"><figcaption>${escapeHtml(placeholder)}</figcaption></figure>`,
		);
		plain = plain.replace(image.token, placeholder);
	}
	return { title, plain: `${plain}\n`, clipboard, preview };
}

function previewPage(article, images) {
	const payload = safeScriptValue({
		html: article.clipboard,
		text: article.plain,
		title: article.title,
	});
	return `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'"><title>${escapeHtml(article.title)} — 专栏交付预览</title><style>
body{margin:0;background:#f1efe8;color:#242821;font-family:system-ui,sans-serif}header,aside,article{box-sizing:border-box;max-width:780px;margin:24px auto;padding:28px;background:#fffdf8;overflow-wrap:anywhere}header h1{font-size:28px;line-height:1.5}article{font-size:18px;line-height:1.95}article h2{font-size:25px;margin-top:1.8em}article h3{font-size:21px}button{padding:10px 16px;margin:4px;border:1px solid #426452;background:white;border-radius:6px;font-size:16px;cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid #b56817}figure{margin:24px 0}img{max-width:100%;height:auto;display:block;margin:auto}figcaption{font-size:14px;color:#555}blockquote{border-left:4px solid #426452;margin:24px 0;padding-left:20px}a{color:#28644c}#manual{white-space:pre-wrap;width:100%;min-height:220px;box-sizing:border-box}#copy-source{position:absolute;left:-100000px;width:720px}#copy-source.manual{position:static;width:auto;border:2px solid #b56817;padding:16px}aside{font-size:14px;color:#4d534a}@media(max-width:600px){header,aside,article{margin:0;padding:22px}article{font-size:17px}}@media print{header button,#status,aside,#copy-source{display:none}body{background:white}}
</style></head><body><header><h1>${escapeHtml(article.title)}</h1><p>标题独立填写；复制正文后，在平台对应占位处上传本包 images 目录中的图片。</p><button id="copy-body" type="button">复制正文富文本</button><button id="copy-title" type="button">复制标题</button><button id="show-manual" type="button">显示手动复制正文</button><p id="status" role="status" aria-live="polite">本地交付已准备，平台粘贴预览待完成。</p></header>
<article id="preview">${article.preview}</article><section id="copy-source" aria-label="手动复制正文">${article.clipboard}</section><aside><p>这是本地排版预览；没有登录、上传图片或发布。富文本复制保留图片占位，不会自动把本地图片上传或嵌入为 Base64。若平台改变格式，请使用 bilibili.txt 恢复段落与完整来源 URL。</p><p>图片来源记录：${images.length ? images.map((image, index) => `${index + 1}. ${escapeHtml(image.file)} — ${image.source === "local_catalog" ? "本地书目提供" : "作者提供"}；${escapeHtml(image.caption)}`).join("<br>") : "本包无图片。"}</p><p>本机可读取封面并不代表获得发行许可；作者需在实际发布前确认图片使用依据。此处仅保存来源说明，不作许可认定。</p><p>当前平台入口：<a href="https://member.bilibili.com/york/read-editor">B 站专栏编辑器</a>。本地复制通过不等于平台兼容性已验证。</p></aside>
<script>
const payload=${payload};
const status=document.getElementById('status');
function manual(){const source=document.getElementById('copy-source');source.classList.add('manual');const range=document.createRange();range.selectNodeContents(source);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);source.scrollIntoView({block:'center'});status.textContent='已显示并选中无本地图的正文，请按 Ctrl+C（Mac 为 Cmd+C）手动复制；仍可改用 bilibili.txt。';}
document.getElementById('show-manual').addEventListener('click',manual);
document.getElementById('copy-body').addEventListener('click',async()=>{try{if(!navigator.clipboard?.write||typeof ClipboardItem==='undefined')throw new Error('clipboard unavailable');await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([payload.html],{type:'text/html'}),'text/plain':new Blob([payload.text],{type:'text/plain'})})]);status.textContent='正文富文本及纯文本已复制；图片仍是占位，请在平台手动上传。';}catch{manual();}});
document.getElementById('copy-title').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(payload.title);status.textContent='标题已复制。';}catch{const range=document.createRange();range.selectNodeContents(document.querySelector('header h1'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent='已选中标题，请按 Ctrl+C（Mac 为 Cmd+C）复制。';}});
</script></body></html>\n`;
}

async function existing(filename) {
	try {
		const stat = await lstat(filename);
		if (!stat.isFile() || stat.isSymbolicLink())
			throw new Error("输出目标不是普通文件");
		return await readFile(filename);
	} catch (error) {
		if (error.code === "ENOENT") return null;
		throw error;
	}
}

export async function exportBilibili(input, output, assetsManifest) {
	await noSymlinks(input);
	await noSymlinks(output);
	const source = await readFile(input, "utf8");
	const clean = await prepareArticle(source);
	publicText(clean, "正文");
	const { images, signature } = await imagesFrom(assetsManifest);
	const article = await adapt(clean, images);
	const order = images.map(
		({ id, caption, after_heading, source: origin, file, sha256 }, index) => ({
			order: index + 1,
			id,
			file,
			after_heading,
			caption,
			sha256,
			source: origin,
			publication_permission: "author_check_pending",
		}),
	);
	const delivery = {
		schema: 1,
		status: "local_ready",
		platform_preview: "pending",
		platform_status: "platform_preview_pending",
		publication: "not_published",
		title: article.title,
		body: "bilibili.html",
		fallback: "bilibili.txt",
		image_order: "asset-order.json",
		images: order.length,
		platform_entry: "https://member.bilibili.com/york/read-editor",
		platform_compatibility: "not_verified",
		image_upload: "manual",
		source_permissions: "author_check_pending",
	};
	const files = new Map(
		Object.entries({
			"bilibili.html": previewPage(article, images),
			"bilibili.txt": article.plain,
			"article.md": clean,
			"title.txt": `${article.title}\n`,
			"asset-order.json": json({ schema: 1, images: order }),
			"delivery.json": json(delivery),
		}).map(([name, content]) => [name, Buffer.from(content)]),
	);
	for (const image of images) files.set(image.file, image.bytes);
	const directory = path.resolve(output);
	const relativeOutput = path.relative(PROJECT, directory);
	if (
		!relativeOutput.startsWith(`..${path.sep}`) &&
		relativeOutput !== ".." &&
		!path.isAbsolute(relativeOutput) &&
		relativeOutput !== ".local" &&
		!relativeOutput.startsWith(`.local${path.sep}`)
	)
		throw new Error(
			"项目内交付产物必须放入私有 .local 目录，不写入公开站点源码或public",
		);
	for (const name of files.keys())
		if (
			path.resolve(input) === path.join(directory, name) ||
			(assetsManifest &&
				path.resolve(assetsManifest) === path.join(directory, name)) ||
			images.some((image) => image.source_path === path.join(directory, name))
		)
			throw new Error("输出不能覆盖输入文件");
	await mkdir(directory, { recursive: true });
	const oldRaw = await existing(path.join(directory, MARKER));
	const previous = oldRaw ? JSON.parse(oldRaw.toString("utf8")) : null;
	if (
		previous &&
		(previous.tool !== "firefly-creator-bilibili" ||
			previous.schema !== 1 ||
			!previous.hashes ||
			typeof previous.hashes !== "object")
	)
		throw new Error("输出目录marker无效或不属于本工具");
	if (previous) {
		const inputs = previous.inputs;
		if (
			!inputs ||
			!/^[0-9a-f]{64}$/.test(inputs.article ?? "") ||
			(inputs.assets !== null && !/^[0-9a-f]{64}$/.test(inputs.assets ?? "")) ||
			previous.input_signature !==
				hash(JSON.stringify({ article: inputs.article, assets: inputs.assets }))
		)
			throw new Error(
				"输出marker输入签名不一致或缺失，请保留原文件并使用新的输出目录",
			);
	}
	for (const name of new Set([
		...files.keys(),
		...Object.keys(previous?.hashes ?? {}),
	])) {
		if (
			path.isAbsolute(name) ||
			name.split(/[\\/]/).includes("..") ||
			name.includes("\\")
		)
			throw new Error("输出marker含不安全路径");
		await noSymlinks(path.join(directory, name));
		const current = await existing(path.join(directory, name));
		if (current && (!previous || previous.hashes[name] !== hash(current)))
			throw new Error(
				`拒绝覆盖已有或人工修改文件：${name}；请使用新的输出目录`,
			);
	}
	const marker = {
		schema: 1,
		tool: "firefly-creator-bilibili",
		inputs: { article: hash(source), assets: signature },
		input_signature: hash(
			JSON.stringify({ article: hash(source), assets: signature }),
		),
		hashes: Object.fromEntries(
			[...files].map(([name, content]) => [name, hash(content)]),
		),
	};
	// Retain previously generated images when a new manifest omits them; never silently delete files.
	for (const [name, fingerprint] of Object.entries(previous?.hashes ?? {}))
		if (!files.has(name)) marker.hashes[name] = fingerprint;
	files.set(MARKER, Buffer.from(json(marker)));
	for (const [name, content] of files) {
		const target = path.join(directory, name);
		if ((await existing(target))?.equals(content)) continue;
		await mkdir(path.dirname(target), { recursive: true });
		await noSymlinks(target);
		const temporary = `${target}.${process.pid}.tmp`;
		try {
			await writeFile(temporary, content, { flag: "wx" });
			await rename(temporary, target);
		} finally {
			await unlink(temporary).catch((error) => {
				if (error.code !== "ENOENT") throw error;
			});
		}
	}
	return {
		output: directory,
		...delivery,
		files: [...files.keys()].filter((name) => name !== MARKER),
	};
}

async function main() {
	const args = process.argv.slice(2);
	if (args.length === 1 && args[0] === "--help") {
		console.log(
			"内部图文适配器；日常使用 creator:system preview --draft <DRAFT-ID> [--assets <vault-relative/assets.json>]\n生成平台待预览图文包，不登录、不上传、不发布。",
		);
		return;
	}
	const options = {};
	for (let index = 0; index < args.length; index += 2) {
		if (
			!["--input", "--output", "--assets"].includes(args[index]) ||
			!args[index + 1] ||
			options[args[index]]
		)
			throw new Error(
				"参数需要 --input <article.md> --output <directory> [--assets <assets.json>]",
			);
		options[args[index]] = args[index + 1];
	}
	if (!options["--input"] || !options["--output"])
		throw new Error("需要 --input 与 --output");
	console.log(
		json(
			await exportBilibili(
				options["--input"],
				options["--output"],
				options["--assets"],
			),
		),
	);
}
if (
	process.argv[1] &&
	import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
)
	main().catch((error) => {
		console.error(error.message);
		process.exitCode = 1;
	});
