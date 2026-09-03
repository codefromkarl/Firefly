/**
 * visual-check.mjs — 改版视觉 QA（无头 Chrome 计算样式断言）
 *
 * 用法：pnpm visual-check
 * 依赖：本机已安装 google-chrome（channel: chrome），pnpm add -D playwright
 * 输出：.redesign-shots/qa-*.png 截图 + 控制台断言结果
 */
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.env.VISUAL_BASE ?? "http://localhost:4321";
const PAGES = [
	{ name: "home", path: "/" },
	{ name: "books", path: "/books/" },
	{ name: "post", path: "/posts/contextatlas-harness-engineering/" },
	{ name: "404", path: "/no-such-page-xyz/" },
];
const OUT = new URL("../.redesign-shots/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const EMOJI_RE =
	/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{2B50}\u{2764}\u{2B55}\u{231A}\u{23E9}-\u{23FA}\u{2614}\u{2615}\u{26A0}\u{26A1}\u{26BD}\u{26BE}\u{2705}\u{2728}\u{274C}\u{274E}\u{2757}\u{2795}-\u{2797}\u{27B0}\u{2934}\u{2935}\u{2B05}-\u{2B07}\u{3030}\u{303D}]/u;

const browser = await chromium.launch({
	channel: "chrome",
	headless: true,
	args: ["--no-sandbox", "--disable-gpu", "--force-dark-mode"],
});

const results = [];
for (const { name, path } of PAGES) {
	const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
	const errors = [];
	page.on("pageerror", (e) => errors.push(`pageerror: ${e.message.slice(0, 200)}`));
	page.on("console", (m) => {
		if (m.type() === "error") errors.push(`console: ${m.text().slice(0, 200)}`);
	});

	await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 45000 });
	await page.evaluate(() => document.fonts.ready);
	await page.waitForTimeout(600);

	const report = await page.evaluate(({ source, flags }) => {
		const emojire = new RegExp(source, flags);
		const r = {};
		const cs = (el, pseudo) => getComputedStyle(el, pseudo);
		r.dark = document.documentElement.classList.contains("dark");
		r.bodyBg = cs(document.body).backgroundColor;
		r.htmlBg = cs(document.documentElement).backgroundColor;
		r.pageVar = cs(document.documentElement).getPropertyValue("--page-bg").trim();
		r.radiusLarge = cs(document.documentElement).getPropertyValue("--radius-large").trim();
		r.primary = cs(document.documentElement).getPropertyValue("--primary").trim();
		r.fontsLoaded = [...document.fonts]
			.filter((f) => f.status === "loaded")
			.map((f) => f.family)
			.filter((v, i, a) => a.indexOf(v) === i)
			.slice(0, 12);
		// 界面文本 emoji 扫描（跳过正文容器）
		const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
		const hits = [];
		for (let n = walker.nextNode(); n; n = walker.nextNode()) {
			const p = n.parentElement;
			if (!p) continue;
			const skipSel = "article, .custom-md, .markdown-body, .dynamic-content, script, style";
			if (p.closest(skipSel)) continue;
			const m = (n.nodeValue || "").match(emojire);
			if (m) hits.push(`${p.tagName.toLowerCase()}.${p.className?.toString().slice(0, 30) || ""}: ${m[0]}`);
		}
		r.uiEmoji = hits.slice(0, 6);
		return r;
	}, { source: EMOJI_RE.source, flags: EMOJI_RE.flags });

	await page.screenshot({ path: `${OUT}qa-${name}.png`, fullPage: false });
	await page.close();
	const known = errors.filter((e) => !/404 \(Not Found\)/.test(e));
	results.push({ name, path, ...report, errors: known.slice(0, 6) });
}

await browser.close();
console.log(JSON.stringify(results, null, 1));
const bad = results.filter(
	(r) =>
		(r.bodyBg === "rgba(0, 0, 0, 0)" && r.htmlBg === "rgba(0, 0, 0, 0)") ||
		r.uiEmoji.length > 0 ||
		r.errors.length > 0,
);
console.log(bad.length ? `⚠ ${bad.length} 项未达标` : "✓ 全部断言通过");
process.exit(bad.length ? 1 : 0);
