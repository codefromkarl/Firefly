import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import { createServer } from "node:http";
import test from "node:test";
import { generateKeyPair, SignJWT } from "jose";
import { chromium } from "playwright";
import {
	analyzeBookmark,
	isPublicAddress,
	parseAnalysis,
	publicBookmarkURL,
	readBookmarkPage,
} from "./analysis.mjs";
import { makeHandler } from "./handler.mjs";

const env = {
	BOOKMARK_ACCESS_ISSUER: "https://test-team.cloudflareaccess.com",
	BOOKMARK_ACCESS_AUD: "bookmarks-test",
	BOOKMARK_ADMIN_EMAIL: "owner@example.net",
};
const base = "/admin/bookmarks/";
const { publicKey, privateKey } = await generateKeyPair("RS256");
const otherKey = (await generateKeyPair("RS256")).privateKey;
const testJWT = (overrides, key = privateKey) =>
	new SignJWT({
		email: env.BOOKMARK_ADMIN_EMAIL,
		exp: Math.floor(Date.now() / 1000) + 900,
		iss: env.BOOKMARK_ACCESS_ISSUER,
		aud: [env.BOOKMARK_ACCESS_AUD],
		...overrides,
	})
		.setProtectedHeader({ alg: "RS256" })
		.sign(key);
const token = await testJWT();
const shell = await readFile(
	new URL("./page.html.txt", import.meta.url),
	"utf8",
);
const client = await readFile(
	new URL("./client.js.txt", import.meta.url),
	"utf8",
);
const ready = {
	state: "ready",
	category: "开发与运维",
	summary: "介绍 Godot 的性能监视器。",
	purpose: "遇到掉帧时检查帧时间和对象数量。",
	quote: "This page explains the performance monitors.",
};

test("全后台默认拒绝；限制签名、应用 audience、管理员邮箱和会话期限", async () => {
	const handle = makeHandler({ shell, client, keys: () => publicKey });
	const origin = "https://codefromkarl.xyz";
	const make = (path, jwt, init = {}) =>
		new Request(origin + path, {
			...init,
			headers: {
				...(jwt && { "cf-access-jwt-assertion": jwt }),
				...init.headers,
			},
		});
	for (const path of [base, `${base}client.js`, `${base}analyze`]) {
		const response = await handle(make(path), env);
		assert.equal(response.status, 403);
		assert.equal(response.headers.get("cache-control"), "private, no-store");
	}
	for (const bad of [
		await testJWT({ aud: ["other-app"] }),
		await testJWT({ iss: "https://other-team.cloudflareaccess.com" }),
		await testJWT({ email: "other@example.net" }),
		await testJWT({ exp: 1 }),
		await testJWT({}, otherKey),
	])
		assert.equal((await handle(make(base, bad), env)).status, 403);
	assert.equal((await handle(make(base, token), {})).status, 403);
	assert.equal(
		(await handle(make(base.slice(0, -1), token), env)).headers.get("location"),
		base,
	);
	const page = await handle(make(base, token), env);
	assert.equal(page.status, 200);
	assert.match(
		page.headers.get("content-security-policy"),
		/frame-ancestors 'none'/,
	);
	assert.match(await page.text(), /Firefly 管理/);
});

test("分析只接收管理员在本站发起的公开 URL；错误可见且不透传凭证", async () => {
	const calls = [];
	const handle = makeHandler({
		shell,
		client,
		keys: () => publicKey,
		analyze(link) {
			calls.push(link.href);
			if (link.pathname === "/unavailable")
				throw new Error("secret internal failure");
			return ready;
		},
	});
	const origin = "https://codefromkarl.xyz";
	const send = (url, requestOrigin = origin) =>
		handle(
			new Request(`${origin + base}analyze`, {
				method: "POST",
				headers: {
					"Cf-Access-Jwt-Assertion": token,
					"Content-Type": "application/json",
					Origin: requestOrigin,
				},
				body: JSON.stringify({ url }),
			}),
			env,
		);
	assert.equal(
		(await send("https://example.org/help", "https://example.org")).status,
		403,
	);
	for (const url of [
		"http://example.org",
		"https://internal.lan",
		"https://127.0.0.1",
		"https://example.org/?token=abc",
		"https://example.org/%6Cogin",
	]) {
		assert.equal((await send(url)).status, 400);
	}
	assert.deepEqual(calls, []);
	assert.deepEqual(
		await (await send("https://example.org/help#private-note")).json(),
		ready,
	);
	assert.deepEqual(calls, ["https://example.org/help"]);
	const failure = await send("https://example.org/unavailable");
	assert.equal(failure.status, 503);
	assert.doesNotMatch(await failure.text(), /secret internal failure/);
});

test("公开解析、重定向和正文证据是独立的门槛", async () => {
	for (const address of [
		"0.0.0.0",
		"127.0.0.1",
		"192.168.1.1",
		"198.18.0.1",
		"100.64.5.1",
		"169.254.169.254",
		"::ffff:127.0.0.1",
		"fd00::3",
		"2001:db8::1",
	]) {
		assert.ok(!isPublicAddress(address), address);
	}
	assert.ok(isPublicAddress("1.1.1.1"));
	assert.ok(isPublicAddress("2606:4700::1111"));
	const link = publicBookmarkURL("https://example.org/article");
	assert.equal(link.href, "https://example.org/article");
	const requested = [];
	const pageFetch =
		({
			redirect,
			privateHost = false,
			result = "Captured article about building a game. It explains several metrics for rendering performance and gives an example.",
		}) =>
		async (target, init) => {
			requested.push(target.href);
			if (target.hostname === "cloudflare-dns.com") {
				assert.equal(init.redirect, "manual");
				const ipv4 = target.searchParams.get("type") === "A";
				return Response.json({
					Status: 0,
					Answer: [
						ipv4
							? { type: 1, data: "1.1.1.1" }
							: { type: 28, data: privateHost ? "fd00::1" : "2606:4700::1111" },
					],
				});
			}
			assert.equal(init.redirect, "manual");
			assert.equal(init.headers.Cookie, undefined);
			return redirect
				? new Response("", { status: 302, headers: { Location: redirect } })
				: new Response(result, { headers: { "Content-Type": "text/plain" } });
		};
	assert.equal(
		(await readBookmarkPage(link, pageFetch({ privateHost: true }))).state,
		"unavailable",
	);
	assert.ok(!requested.includes(link.href));
	assert.equal(
		(
			await readBookmarkPage(
				link,
				pageFetch({ redirect: "https://private.lan/secret" }),
			)
		).state,
		"unavailable",
	);
	assert.ok(!requested.includes("https://private.lan/secret"));
	const captured = await readBookmarkPage(link, pageFetch({}));
	assert.equal(captured.state, "content");
	const analysis = await analyzeBookmark(
		link,
		{
			run(_model, request) {
				assert.equal(request.messages.at(-1).content, captured.evidence);
				assert.doesNotMatch(JSON.stringify(request), /example.org/);
				return { response: { ...ready, quote: "It explains several metrics" } };
			},
		},
		async () => captured,
	);
	assert.equal(analysis.state, "ready");
	assert.equal(analysis.quote, "It explains several metrics");
	assert.throws(() => parseAnalysis(ready, captured.evidence), /Quote missing/);
	assert.equal(
		(await readBookmarkPage(link, pageFetch({ result: "Not enough" }))).state,
		"unavailable",
	);
});

// Fictional responses for UI checks; the browser never requests these source pages.
const workbenchExamples = [
	[
		"Godot Asset Library",
		"开发与运维",
		"在 Godot 项目中找现成插件和示例时使用。",
		"Godot 引擎的资源目录。",
		"Browse assets for the Godot Engine.",
	],
	[
		"网页中文排版指南",
		"教程与资料",
		"排版中文长文时，检查标点、段落和可读行宽。",
		"中文网页排版指南。",
		"Guidelines for typesetting Chinese text on the web.",
	],
	[
		"Astro 构建文档",
		"开发与运维",
		"需要核对 Astro 的静态构建和输出设置时使用。",
		"Astro 构建文档。",
		"Configure the build output for your Astro site.",
	],
	[
		"性能调试手册",
		"开发与运维",
		"遇到掉帧时检查帧时间和对象数量。",
		"性能监视器手册。",
		"This page explains the performance monitors.",
	],
	[
		"Cloudflare Workers 文档",
		"开发与运维",
		"给 Worker 添加环境绑定或检查部署配置时使用。",
		"Workers 配置指南。",
		"Bindings connect a Worker to Cloudflare resources.",
	],
	[
		"Markdown 快速参考",
		"教程与资料",
		"编写项目说明时核对表格、代码块和链接语法。",
		"Markdown 语法备忘。",
		"Use fenced code blocks for multiline code.",
	],
	[
		"开源图标目录",
		"设计与素材",
		"为界面选取同一风格的 SVG 图标。",
		"开源线性图标目录。",
		"Browse the icon set by name and category.",
	],
	[
		"CSS 布局指南",
		"教程与资料",
		"遇到响应式列宽不一致时对照 Grid 的尺寸规则。",
		"CSS Grid 排版参考。",
		"Grid tracks can be sized with minmax().",
	],
	["版本控制工作流"],
	[
		"技术写作实践",
		"研究与阅读",
		"写故障排查文章时，先组织结果、证据和下一步。",
		"面向读者的技术写作建议。",
		"Make the next action clear to the reader.",
	],
];

test("Chrome 真实 HTML 树格式、本地数据、合并式分析、手机搜索和恢复", async () => {
	const analyzed = [];
	let release;
	const handle = makeHandler({
		shell,
		client,
		keys: () => publicKey,
		analyze(link) {
			analyzed.push(link.href);
			const sampleIndex = /^\/workbench-(\d+)$/.exec(link.pathname)?.[1];
			const sample = workbenchExamples[Number(sampleIndex)];
			if (sample) {
				const [, category, purpose, summary, quote] = sample;
				return category
					? { state: "ready", category, purpose, summary, quote }
					: { state: "unavailable", message: "目标网页需要登录，未读取正文" };
			}
			if (link.pathname === "/a-slow")
				return new Promise((resolve) => {
					release = resolve;
				});
			return link.pathname === "/broken"
				? { state: "unavailable", message: "链接已失效（404）" }
				: ready;
		},
	});
	const server = createServer(async (req, res) => {
		const body = [];
		for await (const chunk of req) body.push(chunk);
		const url = new URL(req.url, `http://${req.headers.host}`);
		const response = await handle(
			new Request(url, {
				method: req.method,
				headers: req.headers,
				body: body.length ? Buffer.concat(body) : undefined,
			}),
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
		const unauth = await browser.newPage();
		assert.equal((await unauth.goto(origin + base)).status(), 403);
		await unauth.close();
		const page = await browser.newPage({
			extraHTTPHeaders: { "Cf-Access-Jwt-Assertion": token },
			viewport: { width: 1050, height: 850 },
		});
		const pageErrors = [];
		const outside = [];
		page.on("pageerror", (error) => pageErrors.push(String(error)));
		page.on("request", (request) => {
			if (!request.url().startsWith(origin)) outside.push(request.url());
		});
		assert.equal((await page.goto(origin + base)).status(), 200);
		const upload = (buffer) =>
			page.locator("#file").setInputFiles({
				name: "bookmarks.html",
				mimeType: "text/html",
				buffer: Buffer.from(buffer),
			});
		await page.locator("#import:enabled").waitFor();
		await upload("<html><h1>Not a bookmark file</h1></html>");
		await page.getByText(/这不是 Chrome 书签 HTML/).waitFor();
		const fixture = `<!DOCTYPE NETSCAPE-Bookmark-file-1>
		<TITLE>Bookmarks</TITLE><H1>Bookmarks</H1>
		<DL><p><DT><H3>书签栏</H3>
			<DL><p><DT><H3>项目资料</H3><DL><p>
				<DT><A HREF="https://docs.example.org/godot#private" ADD_DATE="123">Godot 性能监视器</A>
				<DT><A HREF="https://docs.example.org/broken">老教程</A>
				<DT><A HREF="https://wiki.internal/project">内部文档</A>
				<DT><A HREF="javascript:window.archiveInjected=true">网页脚本</A>
			</DL><p>
			<DT><H3>工具</H3><DL><p>
				<DT><A HREF="https://docs.example.org/godot">性能手册</A>
			</DL><p>
			</DL><p>
		</DL><p>
		<img src="https://example.org/do-not-request.png"> `;
		await upload(fixture);
		await page.getByText(/导入 5 条/).waitFor();
		assert.match(await page.locator("#items").innerText(), /书签栏 › 项目资料/);
		assert.match(await page.locator("#items").innerText(), /书签栏 › 工具/);
		assert.equal(await page.getByRole("link", { name: "网页脚本" }).count(), 0);
		assert.equal(
			await page
				.getByRole("checkbox", { name: "选择「内部文档」" })
				.isDisabled(),
			true,
		);
		assert.equal(await page.locator("#analyze").isVisible(), false);
		assert.equal(await page.locator("#bulk").isVisible(), false);
		const pick = page.getByRole("button", { name: "勾选本页可分析项" });
		await pick.click();
		assert.match(
			await page.locator("#selectionInfo").innerText(),
			/已选 3 条书签（2 个不同链接）/,
		);
		const selectionAction = page.getByRole("button", {
			name: "分析所选 2 条",
			exact: true,
		});
		let confirmation;
		page.once("dialog", async (dialog) => {
			confirmation = dialog.message();
			await dialog.dismiss();
		});
		await selectionAction.click();
		assert.match(confirmation, /^分析 2 条公开链接/);
		assert.equal(analyzed.length, 0);
		await page.getByRole("button", { name: "清除选择" }).click();
		assert.equal(await selectionAction.isVisible(), false);
		await pick.click();
		page.once("dialog", (dialog) => dialog.accept());
		await selectionAction.click();
		await page.getByText(/处理 2 条，生成用途 1 条/).waitFor();
		assert.deepEqual(
			new Set(analyzed),
			new Set([
				"https://docs.example.org/godot",
				"https://docs.example.org/broken",
			]),
		);
		assert.equal(analyzed.length, 2);
		assert.equal(await page.getByText(ready.purpose).count(), 2);
		const detailsButton = page.getByRole("button", {
			name: "查看「Godot 性能监视器」详情",
		});
		await detailsButton.click();
		const detail = page.getByRole("dialog", { name: "Godot 性能监视器" });
		assert.match(await detail.innerText(), /建议分类.*什么时候用.*原文依据/s);
		assert.equal(await detail.locator("blockquote").innerText(), ready.quote);
		assert.equal(
			await detail.getByRole("link", { name: "打开来源" }).getAttribute("href"),
			"https://docs.example.org/godot#private",
		);
		await page.keyboard.press("Escape");
		assert.equal(await detail.isVisible(), false);
		assert.equal(
			await detailsButton.evaluate(
				(element) => document.activeElement === element,
			),
			true,
		);
		await detailsButton.click();
		await detail
			.getByRole("textbox", { name: "我的收藏理由" })
			.fill("对比目标机器的帧时间");
		await detail.getByRole("button", { name: "保存备注" }).click();
		await detail.getByText("已保存备注。").waitFor();
		await detail.getByRole("button", { name: "关闭" }).click();
		await page.reload();
		await page.getByText(ready.purpose).first().waitFor();
		await upload(fixture);
		await page.getByText(/导入 0 条，跳过 5 条/).waitFor();
		await page.locator("#search").fill("目标机器");
		assert.equal(await page.locator("#items li.item").count(), 1);
		await page.locator("#search").fill("");
		await page.locator("#category").selectOption("开发与运维");
		assert.equal(await page.locator("#items li.item").count(), 2);
		await page.locator("#category").selectOption("");
		await page.locator("#state").selectOption("unavailable");
		assert.match(
			await page.locator("#items").innerText(),
			/老教程.*链接已失效/s,
		);
		await page.getByRole("button", { name: "查看「老教程」详情" }).click();
		const unavailable = page.getByRole("dialog", { name: "老教程" });
		await unavailable.getByText("无原文可核对。").waitFor();
		assert.equal(await unavailable.locator("blockquote").isVisible(), false);
		assert.equal(await unavailable.getByText("建议分类").isVisible(), false);
		await unavailable.getByRole("button", { name: "关闭" }).click();
		await page.locator("#state").selectOption("");
		await page.getByRole("button", { name: "查看「网页脚本」详情" }).click();
		assert.equal(
			await page.getByRole("link", { name: "打开来源" }).isVisible(),
			false,
		);
		await page.keyboard.press("Escape");
		await page.setViewportSize({ width: 390, height: 844 });
		assert.equal(
			await page.evaluate(
				() => document.documentElement.scrollWidth <= innerWidth,
			),
			true,
		);
		await upload(`<DL><p><DT><A HREF="https://docs.example.org/a-slow">慢响应</A>
			<DT><A HREF="https://docs.example.org/b-fast">待续分析</A></DL>`);
		await page.getByText(/导入 2 条/).waitFor();
		page.once("dialog", (dialog) => dialog.accept());
		await page.getByText("更多操作", { exact: true }).click();
		await page.locator("#bulk").click();
		await page.getByText("正在分析 1 / 2 条").waitFor();
		await page.locator("#pause").click();
		await page.getByText("当前这条处理完就暂停…").waitFor();
		assert.equal(typeof release, "function");
		release(ready);
		await page.getByText(/已暂停。处理 1 \/ 2 条/).waitFor();
		assert.equal(analyzed.at(-1), "https://docs.example.org/a-slow");
		await page.reload();
		await page.getByText("更多操作", { exact: true }).click();
		await page.locator("#bulk:enabled").waitFor();
		page.once("dialog", (dialog) => dialog.accept());
		await page.locator("#bulk").click();
		await page.getByText(/处理 1 条，生成用途 1 条/).waitFor();
		assert.equal(analyzed.at(-1), "https://docs.example.org/b-fast");
		const samplePage = await browser.newPage({
			extraHTTPHeaders: { "Cf-Access-Jwt-Assertion": token },
			viewport: { width: 1220, height: 960 },
		});
		samplePage.on("pageerror", (error) => pageErrors.push(String(error)));
		samplePage.on("request", (request) => {
			if (!request.url().startsWith(origin)) outside.push(request.url());
		});
		const screenshot = async (name) => {
			if (!process.env.BOOKMARK_QA_DIR) return;
			await mkdir(process.env.BOOKMARK_QA_DIR, { recursive: true });
			await samplePage.screenshot({
				path: `${process.env.BOOKMARK_QA_DIR}/${name}.png`,
			});
		};
		await samplePage.goto(origin + base);
		await samplePage.locator("#import:enabled").waitFor();
		await screenshot("firefly-workbench-empty");
		const ten = `<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p><DT><H3>公开参考</H3><DL><p>${workbenchExamples
			.map(
				([title], index) =>
					`<DT><A HREF="https://docs.example.org/workbench-${index}">${title}</A>`,
			)
			.join("")}</DL></DL>`;
		await samplePage.locator("#file").setInputFiles({
			name: "ten-public.html",
			mimeType: "text/html",
			buffer: Buffer.from(ten),
		});
		await samplePage.getByText("共 10 条书签").waitFor();
		assert.equal(await samplePage.locator("#items li.item").count(), 10);
		assert.equal(await samplePage.locator("#analyze").isVisible(), false);
		await samplePage.getByRole("button", { name: "勾选本页可分析项" }).click();
		await samplePage
			.getByRole("button", { name: "分析所选 10 条", exact: true })
			.waitFor();
		await screenshot("firefly-workbench-selected");
		const previousCount = analyzed.length;
		samplePage.once("dialog", (dialog) => dialog.accept());
		await samplePage
			.getByRole("button", { name: "分析所选 10 条", exact: true })
			.click();
		await samplePage
			.getByText(/处理 10 条，生成用途 9 条，未生成 1 条/)
			.waitFor();
		assert.equal(analyzed.length - previousCount, 10);
		assert.equal(await samplePage.locator("#analyze").isVisible(), false);
		await screenshot("firefly-workbench-reviewed");
		await samplePage
			.getByRole("button", { name: "查看「Godot Asset Library」详情" })
			.click();
		await samplePage
			.getByRole("dialog")
			.getByText(/在 Godot 项目中找现成插件/)
			.waitFor();
		await screenshot("firefly-workbench-evidence");
		await samplePage.setViewportSize({ width: 390, height: 844 });
		assert.equal(
			await samplePage.evaluate(
				() => document.documentElement.scrollWidth <= innerWidth,
			),
			true,
		);
		await screenshot("firefly-workbench-mobile-detail");
		await samplePage.keyboard.press("Escape");
		assert.equal(
			await samplePage.evaluate(
				() => document.documentElement.scrollWidth <= innerWidth,
			),
			true,
		);
		await screenshot("firefly-workbench-mobile");
		assert.deepEqual(outside, []);
		assert.deepEqual(pageErrors, []);
	} finally {
		release?.(ready);
		await browser?.close();
		await new Promise((resolve) => server.close(resolve));
	}
});
