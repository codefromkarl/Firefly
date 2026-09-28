import { isIP } from "node:net";
import { createMarkdownProcessor } from "@astrojs/markdown-remark";

function publicUrl(value) {
	let url;
	try {
		url = new URL(value);
	} catch {
		throw new Error(`只允许完整公开 HTTPS 链接：${value}`);
	}
	const hostname = url.hostname.replace(/^\[|\]$/g, "").replace(/\.$/, "");
	if (
		url.protocol !== "https:" ||
		url.username ||
		url.password ||
		isIP(hostname) ||
		!hostname.includes(".") ||
		/(?:^|\.)(?:localhost|local|internal|lan|home|test|invalid)$/i.test(
			hostname,
		)
	) {
		throw new Error(`不允许非公开链接：${value}`);
	}
}

export async function prepareArticle(source) {
	let markdown = source.replace(/^\uFEFF/, "").replace(/\r\n/g, "\n");
	if (markdown.startsWith("---\n")) {
		const end = markdown.indexOf("\n---", 4);
		if (end < 0 || !/^\n---(?:\n|$)/.test(markdown.slice(end)))
			throw new Error("Frontmatter 未正确闭合");
		markdown = markdown.slice(end + 4).trimStart();
	}
	if (!markdown.trim()) throw new Error("稿件正文为空");
	if (
		/!?\[\[|%%|(?:file|obsidian):\/\/|(?:\/home\/|\/Users\/|[A-Za-z]:\\)/i.test(
			markdown,
		)
	) {
		throw new Error(
			"正文含私人双链、内部注释或本地路径；请移至项目卡，公开稿只保留公开引用",
		);
	}
	markdown = `${markdown.trim()}\n`;
	const validate = () => (tree) => {
		function walk(node) {
			if (node.type === "html")
				throw new Error("公开稿不接受原始 HTML，请使用普通 Markdown");
			if (node.type === "image" || node.type === "imageReference")
				throw new Error(
					"正文图片请改用专栏素材清单登记，再在平台编辑器逐张上传",
				);
			if (node.type === "link" || node.type === "definition")
				publicUrl(node.url);
			for (const child of node.children || []) walk(child);
		}
		walk(tree);
	};
	const processor = await createMarkdownProcessor({
		syntaxHighlight: false,
		remarkPlugins: [validate],
	});
	await processor.render(markdown);
	return markdown;
}
