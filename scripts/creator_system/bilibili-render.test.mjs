import assert from "node:assert/strict";
import {
	mkdir,
	mkdtemp,
	readFile,
	rm,
	symlink,
	writeFile,
} from "node:fs/promises";
import path from "node:path";
import { test } from "node:test";
import { chromium } from "playwright";
import sharp from "sharp";
import { exportBilibili } from "./bilibili-render.mjs";

async function fixture(fn) {
	await mkdir(".local/validation", { recursive: true });
	const root = await mkdtemp(path.resolve(".local/validation/bilibili-test-"));
	try {
		const input = path.join(root, "input.md");
		await writeFile(
			input,
			"---\nprivate: /home/private\n---\n# 独立标题\n\n## 观点\n\n**加粗**与[原始来源](https://example.com/paper?a=1&b=2)。\n\n> 保留引用\n\n- 第一项\n- 第二项\n",
		);
		await fn({ root, input, output: path.join(root, "output") });
	} finally {
		await rm(root, { recursive: true, force: true });
	}
}

async function makeManifest(root, entries) {
	await sharp({
		create: { width: 32, height: 24, channels: 4, background: "#dcca99" },
	})
		.png()
		.toFile(path.join(root, "cover.png"));
	const manifest = path.join(root, "assets.json");
	await writeFile(
		manifest,
		JSON.stringify({
			schema: 1,
			images: entries ?? [
				{
					id: "cover",
					path: "cover.png",
					caption: "封面展示",
					after_heading: "观点",
					source: "local_catalog",
				},
			],
		}),
	);
	return manifest;
}

test("标题独立、公开引用保留、manifest图片转换及无原路径泄漏", async () =>
	fixture(async ({ root, input, output }) => {
		const result = await exportBilibili(
			input,
			output,
			await makeManifest(root),
		);
		assert.equal(result.platform_compatibility, "not_verified");
		assert.equal(
			await readFile(path.join(output, "title.txt"), "utf8"),
			"独立标题\n",
		);
		const text = await readFile(path.join(output, "bilibili.txt"), "utf8");
		assert.ok(!text.includes("独立标题"));
		assert.match(text, /https:\/\/example.com\/paper\?a=1&b=2/);
		assert.match(text, /【插图 1：封面展示】/);
		const order = JSON.parse(
			await readFile(path.join(output, "asset-order.json"), "utf8"),
		);
		assert.equal(order.images[0].file, "images/01-cover.png");
		assert.equal(
			order.images[0].publication_permission,
			"author_check_pending",
		);
		for (const name of [
			"bilibili.html",
			"bilibili.txt",
			"article.md",
			"asset-order.json",
			"delivery.json",
		]) {
			const content = await readFile(path.join(output, name), "utf8");
			assert.ok(!content.includes("/home/private"));
			assert.ok(!content.includes(root));
		}
	}));

test("表格降级为有表头的段落，代码作为字面引用，不发送GFM表格", async () =>
	fixture(async ({ input, output }) => {
		await writeFile(
			input,
			"# 标题\n\n| 项目 | 来源 |\n| --- | --- |\n| 金额 | [原文](https://example.com) |\n\n```text\n<script>literal</script>\n```\n",
		);
		await exportBilibili(input, output);
		const html = await readFile(path.join(output, "bilibili.html"), "utf8");
		assert.match(html, /项目：/);
		assert.match(html, /来源：/);
		assert.ok(!html.includes("<table"));
		assert.ok(!html.includes("<pre"));
		assert.match(html, /&lt;script&gt;literal&lt;\/script&gt;/);
	}));

test("重复导出保护人工修改、无关文件及符号链接", async () =>
	fixture(async ({ root, input, output }) => {
		await exportBilibili(input, output);
		await writeFile(path.join(output, "user.txt"), "keep");
		await exportBilibili(input, output);
		assert.equal(await readFile(path.join(output, "user.txt"), "utf8"), "keep");
		await writeFile(path.join(output, "bilibili.txt"), "manual edits");
		await assert.rejects(exportBilibili(input, output), /拒绝覆盖/);
		const linked = path.join(root, "linked");
		await symlink(output, linked);
		await assert.rejects(exportBilibili(input, linked), /符号链接/);
	}));

test("危险输入、非图片、越界路径、重复id和不存在插入标题拒绝", async () =>
	fixture(async ({ root, input, output }) => {
		for (const body of [
			"# 标题\n\n[[私有笔记]]",
			"# 标题\n\n<script>alert(1)</script>",
			"# 标题\n\n![秘密](file:///home/private)",
			"# 标题\n\n~~不能误当加粗~~",
			"# 标题\n\n- [ ] 未完成",
		]) {
			await writeFile(input, body);
			await assert.rejects(exportBilibili(input, output));
		}
		await writeFile(input, "# 标题\n\n## 观点\n\n正文");
		for (const entry of [
			{ id: "x", path: "../outside.png", caption: "x" },
			{ id: "x", path: "cover.png", caption: "/home/user/secret" },
			{ id: "x", path: "cover.png", caption: "x", after_heading: "不存在" },
			{ id: "x", path: "not-image.txt", caption: "x" },
		])
			await assert.rejects(
				exportBilibili(input, output, await makeManifest(root, [entry])),
			);
		await symlink(path.join(root, "cover.png"), path.join(root, "link.png"));
		await assert.rejects(
			exportBilibili(
				input,
				output,
				await makeManifest(root, [
					{ id: "link", path: "link.png", caption: "x" },
				]),
			),
			/符号链接/,
		);
		const dup = { id: "x", path: "cover.png", caption: "x" };
		await assert.rejects(
			exportBilibili(input, output, await makeManifest(root, [dup, dup])),
			/唯一/,
		);
	}));

test("常见Windows私路径拒绝，marker签名损坏不能默默恢复", async () =>
	fixture(async ({ root, input, output }) => {
		for (const privatePath of [
			"D:/private/notes.md",
			String.raw`\\NAS\private\notes.md`,
		]) {
			await writeFile(input, `# 标题\n\n${privatePath}`);
			await assert.rejects(exportBilibili(input, output), /本地路径/);
		}
		await writeFile(input, "# 标题\n\n正文");
		const manifest = await makeManifest(root, [
			{ id: "cover", path: "cover.png", caption: "封面" },
		]);
		await exportBilibili(input, output, manifest);
		const markerPath = path.join(output, ".creator-bilibili.json");
		const marker = JSON.parse(await readFile(markerPath, "utf8"));
		const bodyBefore = await readFile(
			path.join(output, "bilibili.txt"),
			"utf8",
		);
		marker.input_signature = "corrupted-signature";
		await writeFile(markerPath, JSON.stringify(marker));
		await assert.rejects(exportBilibili(input, output, manifest), /输入签名/);
		assert.equal(
			await readFile(path.join(output, "bilibili.txt"), "utf8"),
			bodyBefore,
		);
	}));

test("浏览器富文本复制至本地contenteditable保留标签、链接和图片占位；失败可手动选中", async () =>
	fixture(async ({ root, input, output }) => {
		await exportBilibili(input, output, await makeManifest(root));
		const browser = await chromium.launch({ headless: true });
		try {
			const page = await browser.newPage();
			await page.goto(`file://${path.join(output, "bilibili.html")}`);
			await page.evaluate(() => {
				window.copied = null;
				Object.defineProperty(navigator, "clipboard", {
					configurable: true,
					value: {
						write: async (items) => {
							window.copied = items;
						},
						writeText: async () => {},
					},
				});
			});
			await page.click("#copy-body");
			const facts = await page.evaluate(async () => {
				const item = window.copied[0];
				const html = await (await item.getType("text/html")).text();
				const text = await (await item.getType("text/plain")).text();
				const target = document.createElement("div");
				target.contentEditable = "true";
				target.id = "paste-test";
				document.body.append(target);
				target.focus();
				document.execCommand("insertHTML", false, html);
				return {
					headings: target.querySelectorAll("h2").length,
					bold: target.querySelectorAll("strong,b").length,
					quote: target.querySelectorAll("blockquote").length,
					list: target.querySelectorAll("li").length,
					images: target.querySelectorAll("img").length,
					placeholder: target.textContent.includes("【插图 1：封面展示】"),
					link: target.querySelector("a")?.href,
					text,
					previewImage: document.querySelector("#preview img")?.naturalWidth,
				};
			});
			assert.equal(facts.headings, 1);
			assert.equal(facts.bold, 1);
			assert.equal(facts.quote, 1);
			assert.equal(facts.list, 2);
			assert.equal(facts.images, 0);
			assert.equal(facts.placeholder, true);
			assert.equal(facts.previewImage, 32);
			assert.match(facts.link, /https:\/\/example.com\/paper/);
			assert.match(facts.text, /https:\/\/example.com\/paper/);
			await page.evaluate(() =>
				Object.defineProperty(navigator, "clipboard", {
					configurable: true,
					value: {
						write: async () => {
							throw new Error("blocked");
						},
					},
				}),
			);
			await page.click("#copy-body");
			assert.equal(
				await page
					.locator("#copy-source")
					.evaluate((element) => element.classList.contains("manual")),
				true,
			);
			assert.match(await page.locator("#status").textContent(), /Ctrl\+C/);
			assert.match(
				await page.evaluate(() => window.getSelection().toString()),
				/【插图 1/,
			);
		} finally {
			await browser.close();
		}
	}));
