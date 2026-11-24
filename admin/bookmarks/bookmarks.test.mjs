import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import test from "node:test";
import { generateKeyPair, SignJWT } from "jose";
import { chromium } from "playwright";
import { makeHandler } from "./handler.mjs";

const base = "/admin/bookmarks/";
const importPath = `${base}import/`;
const env = {
	BOOKMARK_ACCESS_ISSUER: "https://test-team.cloudflareaccess.com",
	BOOKMARK_ACCESS_AUD: "bookmarks-test",
	BOOKMARK_ADMIN_EMAIL: "owner@example.net",
};
const { publicKey, privateKey } = await generateKeyPair("RS256");
const sign = async (overrides = {}, key = privateKey) =>
	new SignJWT({
		email: env.BOOKMARK_ADMIN_EMAIL,
		exp: Math.floor(Date.now() / 1000) + 900,
		iss: env.BOOKMARK_ACCESS_ISSUER,
		aud: [env.BOOKMARK_ACCESS_AUD],
		...overrides,
	})
		.setProtectedHeader({ alg: "RS256" })
		.sign(key);
const token = await sign();
const handle = makeHandler({
	shell: await readFile(new URL("./page.html.txt", import.meta.url), "utf8"),
	importShell: await readFile(
		new URL("./import.html.txt", import.meta.url),
		"utf8",
	),
	client: await readFile(new URL("./client.js.txt", import.meta.url), "utf8"),
	banner: await readFile(
		new URL("../../src/assets/images/home-bg.webp", import.meta.url),
	),
	keys: () => publicKey,
});

test("所有页面资源维持管理员校验和禁止缓存，分析接口已移除", async () => {
	const get = (path, jwt, method = "GET", bindings = env) =>
		handle(
			new Request(`https://codefromkarl.xyz${path}`, {
				method,
				headers: jwt ? { "cf-access-jwt-assertion": jwt } : {},
			}),
			bindings,
		);
	for (const path of [
		base,
		importPath,
		importPath.slice(0, -1),
		`${base}client.js`,
		`${base}banner.webp`,
	]) {
		const response = await get(path);
		assert.equal(response.status, 403);
		assert.equal(response.headers.get("cache-control"), "private, no-store");
	}
	const wrongKey = (await generateKeyPair("RS256")).privateKey;
	for (const bad of [
		await sign({ aud: ["other-app"] }),
		await sign({ iss: "https://other-team.cloudflareaccess.com" }),
		await sign({ email: "other@example.net" }),
		await sign({ exp: 1 }),
		await sign({}, wrongKey),
	])
		assert.equal((await get(base, bad)).status, 403);
	assert.equal((await get(base, token, "GET", {})).status, 403);
	assert.equal(
		(await get(base.slice(0, -1), token)).headers.get("location"),
		base,
	);
	const page = await get(base, token);
	assert.equal(page.status, 200);
	assert.match(
		page.headers.get("content-security-policy"),
		/connect-src 'none'/,
	);
	assert.match(
		page.headers.get("content-security-policy"),
		/frame-ancestors 'none'/,
	);
	const html = await page.text();
	assert.match(html, /书签 · CodeFromKarl/);
	assert.doesNotMatch(html, /<button|type="file"|导入结果/);
	const editor = await get(importPath, token);
	assert.equal(editor.status, 200);
	assert.match(await editor.text(), /选择 JSON 文件/);
	assert.equal(
		(await get(importPath.slice(0, -1), token)).headers.get("location"),
		importPath,
	);
	assert.equal((await get(importPath, token, "POST")).status, 405);
	assert.match(
		(await get(`${base}client.js`, token)).headers.get("content-type"),
		/javascript/,
	);
	const banner = await get(`${base}banner.webp`, token);
	assert.equal(banner.status, 200);
	assert.equal(banner.headers.get("content-type"), "image/webp");
	assert.equal(
		Buffer.from(await banner.arrayBuffer())
			.subarray(8, 12)
			.toString(),
		"WEBP",
	);
	assert.equal(
		await (await get(`${base}banner.webp`, token, "HEAD")).text(),
		"",
	);
	assert.equal((await get(`${base}analyze`, token, "POST")).status, 404);
	assert.equal((await get(base, token, "POST")).status, 405);
});

test("Chrome 只导入整理好的结果；220 行可按分类筛选、刷新，旧库不改", async () => {
	const requests = [];
	const server = createServer(async (req, res) => {
		const url = new URL(req.url, `http://${req.headers.host}`);
		requests.push([req.method, url.pathname]);
		const response = await handle(
			new Request(url, { method: req.method, headers: req.headers }),
			env,
		);
		res.writeHead(response.status, Object.fromEntries(response.headers));
		res.end(Buffer.from(await response.arrayBuffer()));
	});
	await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
	let browser;
	try {
		browser = await chromium.launch({ channel: "chrome", headless: true });
		const origin = `http://127.0.0.1:${server.address().port}`;
		const context = await browser.newContext({
			extraHTTPHeaders: { "Cf-Access-Jwt-Assertion": token },
			viewport: { width: 1150, height: 900 },
		});
		const page = await context.newPage();
		const importer = await context.newPage();
		const outside = [];
		const errors = [];
		for (const tab of [page, importer]) {
			tab.on("request", (request) => {
				if (!request.url().startsWith(origin)) outside.push(request.url());
			});
			tab.on("pageerror", (error) => errors.push(String(error)));
		}
		assert.equal((await page.goto(origin + base)).status(), 200);
		const oldBookmark = {
			id: "legacy",
			title: "原始书签",
			note: "旧备注不可覆盖",
		};
		await page.evaluate(
			(record) =>
				new Promise((resolve, reject) => {
					const request = indexedDB.open("firefly-admin-bookmarks", 1);
					request.onupgradeneeded = () =>
						request.result.createObjectStore("bookmarks", { keyPath: "id" });
					request.onsuccess = () => {
						const db = request.result;
						const tx = db.transaction("bookmarks", "readwrite");
						tx.objectStore("bookmarks").put(record);
						tx.oncomplete = () => {
							db.close();
							resolve();
						};
						tx.onabort = () => reject(tx.error);
					};
					request.onerror = () => reject(request.error);
				}),
			oldBookmark,
		);
		assert.equal(await page.getByRole("button").count(), 0);
		assert.equal(await page.locator("input[type=file]").count(), 0);
		assert.equal((await importer.goto(origin + importPath)).status(), 200);
		const upload = (text, name = "bookmarks.json") =>
			importer.locator("#file").setInputFiles({
				name,
				mimeType: "application/json",
				buffer: Buffer.from(text),
			});
		await importer.locator("#import:enabled").waitFor();
		assert.equal(await importer.getByRole("button").count(), 1);
		await upload(
			"<DL><DT><A HREF='https://example.org'>Not a result</A></DL>",
			"bookmarks.html",
		);
		await importer.getByText(/不能导入 Chrome 原始 HTML/).waitFor();
		const examples = [
			{
				title: "WinBoat",
				url: "https://github.com/winboat-org/winboat",
				purpose: "在 Linux 桌面打开需要 Windows 的应用。",
				category: " 开发工具 ",
				type: " 开源项目 ",
			},
			{
				title: "Pretext",
				url: "https://github.com/chenglou/pretext",
				purpose: "在渲染前计算多行文字的换行和尺寸。",
				category: "开发工具",
				type: "开源项目",
			},
			{
				title: "Godot Asset Library",
				url: "https://godotengine.org/asset-library/asset",
				purpose: "按 Godot 版本和许可证查找可复用的插件与示例。",
				category: "游戏开发",
				type: "资源目录",
			},
			{
				title: "赫蹏",
				url: "https://sivan.github.io/heti/",
				purpose: "改善中文网页的标点、混排和长文阅读体验。",
				category: "网页设计",
				type: "项目演示",
			},
			{
				title: "Chrome 设置",
				url: "chrome://settings/",
				purpose: "调整浏览器的隐私和语言设置。",
			},
		];
		const records = [
			...examples,
			...Array.from({ length: 214 }, (_, i) => ({
				title: `本地测试书签 ${i + 1}`,
				url: `https://example.org/bookmark-${i}`,
				purpose: "检查用途在只读表格中的阅读效果。",
			})),
			{
				title: "<img src=https://example.org/x>",
				url: "javascript:window.injected=true",
				purpose: "<b>只是普通文本。</b>",
			},
		];
		await upload(JSON.stringify(records));
		await importer.getByText("已保存到当前浏览器。").waitFor();
		await page.reload();
		await page.getByText("220 条", { exact: true }).waitFor();
		assert.deepEqual(await page.locator("thead th").allTextContents(), [
			"书签",
			"类型",
			"用途",
		]);
		assert.equal(await page.locator("tbody tr").count(), 220);
		assert.deepEqual(
			await page
				.locator("tbody .type")
				.allTextContents()
				.then((types) => types.slice(0, 5)),
			["开源项目", "开源项目", "资源目录", "项目演示", "未标注"],
		);
		const filter = page.getByRole("combobox", { name: "按分类筛选" });
		assert.deepEqual(
			new Set(await filter.locator("option").allTextContents()),
			new Set(["全部分类", "开发工具", "游戏开发", "网页设计", "未分类"]),
		);
		await filter.selectOption("开发工具");
		assert.deepEqual(
			await page.locator("tbody tr td:first-child").allTextContents(),
			["WinBoat", "Pretext"],
		);
		await page.getByText("2 / 220 条", { exact: true }).waitFor();
		await filter.selectOption("未分类");
		assert.equal(await page.locator("tbody tr").count(), 216);
		await filter.selectOption("游戏开发");
		assert.equal(
			await page.locator("tbody tr td:first-child").innerText(),
			"Godot Asset Library",
		);
		await page.reload();
		await page.getByText("220 条", { exact: true }).waitFor();
		assert.equal(await filter.inputValue(), "");
		assert.equal(await page.locator("tbody tr").count(), 220);
		assert.equal(
			await page.locator("tbody tr").last().locator("td").nth(2).innerText(),
			records.at(-1).purpose,
		);
		assert.equal(
			await page.locator("tbody img, tbody a[href^='javascript:']").count(),
			0,
		);
		assert.equal(
			await page.getByRole("link", { name: "Chrome 设置" }).count(),
			0,
		);
		assert.equal(
			await page.getByRole("link", { name: "WinBoat" }).getAttribute("href"),
			examples[0].url,
		);
		assert.ok(
			requests.some(
				([method, path]) => method === "GET" && path === `${base}banner.webp`,
			),
		);
		await page.reload();
		await page.getByText("220 条", { exact: true }).waitFor();
		assert.equal(await page.locator("tbody tr").count(), 220);
		const qa = process.env.BOOKMARK_QA_DIR;
		if (qa) {
			await mkdir(qa, { recursive: true });
			await page.screenshot({ path: `${qa}/firefly-static-table.png` });
		}
		await page.setViewportSize({ width: 390, height: 844 });
		assert.equal(
			await page.evaluate(
				() => document.documentElement.scrollWidth <= innerWidth,
			),
			true,
		);
		if (qa)
			await page.screenshot({ path: `${qa}/firefly-static-table-mobile.png` });
		await upload(JSON.stringify([{ ...examples[0], purpose: "" }]));
		await importer.getByText(/第 1 条需要有效网址/).waitFor();
		await upload(JSON.stringify([{ ...examples[0], category: 123 }]));
		await importer.getByText(/第 1 条的分类须为/).waitFor();
		await upload(JSON.stringify([{ ...examples[0], type: ["开源项目"] }]));
		await importer.getByText(/第 1 条的类型须为/).waitFor();
		await page.reload();
		await page.getByText("220 条", { exact: true }).waitFor();
		assert.equal(await page.locator("tbody tr").count(), 220);
		const oldFormat = examples.map(({ title, url, purpose }) => ({
			title,
			url,
			purpose,
		}));
		importer.once("dialog", (dialog) => dialog.dismiss());
		await upload(JSON.stringify(oldFormat));
		await importer.locator("#import:enabled").waitFor();
		await page.reload();
		await page.getByText("220 条", { exact: true }).waitFor();
		assert.equal(await page.locator("tbody tr").count(), 220);
		importer.once("dialog", (dialog) => dialog.accept());
		await upload(JSON.stringify(oldFormat));
		await importer.getByText("当前表格有 5 条书签。").waitFor();
		await importer.getByRole("link", { name: "查看书签" }).click();
		await importer.getByText("5 条", { exact: true }).waitFor();
		assert.equal(await importer.getByRole("button").count(), 0);
		await page.reload();
		await page.getByText("5 条", { exact: true }).waitFor();
		assert.equal(await page.locator("tbody tr").count(), 5);
		assert.equal(await page.locator("#category").isVisible(), false);
		assert.deepEqual(
			await page.locator("tbody .type").allTextContents(),
			Array(5).fill("未标注"),
		);
		const legacy = await page.evaluate(
			() =>
				new Promise((resolve, reject) => {
					const request = indexedDB.open("firefly-admin-bookmarks", 1);
					request.onsuccess = () => {
						const db = request.result;
						const get = db
							.transaction("bookmarks")
							.objectStore("bookmarks")
							.get("legacy");
						get.onsuccess = () => {
							db.close();
							resolve(get.result);
						};
						get.onerror = () => reject(get.error);
					};
					request.onerror = () => reject(request.error);
				}),
		);
		assert.deepEqual(legacy, oldBookmark);
		assert.deepEqual(outside, []);
		assert.deepEqual(errors, []);
		assert.ok(requests.every(([method]) => method === "GET"));
	} finally {
		await browser?.close();
		await new Promise((resolve) => server.close(resolve));
	}
});
