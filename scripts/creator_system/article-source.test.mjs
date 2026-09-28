import assert from "node:assert/strict";
import { test } from "node:test";
import { prepareArticle } from "./article-source.mjs";

test("拒绝私有链接、主动内容、本地附件和异常frontmatter", async () => {
	for (const source of [
		"[[私有观点]]",
		"%%内部内容%%",
		"/home/user/secret",
		"[文件](file:///private)",
		"[本地](../draft.md)",
		"[x](javascript:alert%281%29)",
		"<script>alert(1)</script>",
		"![图](https://example.com/a.png)",
		"---\na: b",
		"[内部](https://localhost/private)",
		"[内部](https://192.168.1.2/private)",
		"[凭据](https://user:pass@example.com/)",
		"[内部](https://10.0.0.2)",
		"[内部](https://[fd00::1])",
		"[内部](https://machine.localhost)",
	])
		await assert.rejects(prepareArticle(source));
	const safe = await prepareArticle("# 标题\n\n`<script>` & 说明");
	assert.match(safe, /`<script>`/);
});

test("剥离私有元数据并保留公开引用及原始正文", async () => {
	const source =
		"# 标题\n\n[来源][paper]\n\n[paper]: https://example.com/paper?a=1&b=2\n";
	assert.equal(
		await prepareArticle(`---\nprivate: /home/private\n---\n${source}`),
		source,
	);
});
