// VISUAL_BASE=http://127.0.0.1:4396 node scripts/check-reading-guide.mjs
import assert from "node:assert/strict";
import { mkdir, readdir, readFile } from "node:fs/promises";
import matter from "gray-matter";
import { chromium } from "playwright";

const base = process.env.VISUAL_BASE ?? "http://localhost:4321";
const out = new URL("../.redesign-shots/", import.meta.url).pathname;
await mkdir(out, { recursive: true });
const libraryRoot = new URL("../src/content/books/", import.meta.url);
const records = (
	await Promise.all(
		(
			await readdir(libraryRoot, { withFileTypes: true })
		)
			.filter((entry) => entry.isDirectory())
			.map(async ({ name }) => ({
				slug: name,
				...matter(
					await readFile(new URL(`${name}/index.md`, libraryRoot), "utf8"),
				).data,
			})),
	)
).filter((book) => !book.draft);
const works = new Set(records.map((b) => b.listedWith ?? b.slug));
const browser = await chromium.launch({ channel: "chrome" });
try {
	for (const width of [1440, 390]) {
		const page = await browser.newPage({
			viewport: { width, height: 900 },
			colorScheme: width === 390 ? "dark" : "light",
		});
		const errors = [];
		page.on("pageerror", (e) => errors.push(e.message));
		const hub = page.locator("#reading-guide");
		const search = page.locator("#book-search");
		const filter = (t) =>
			hub
				.getByRole("navigation", { name: "学科领域" })
				.getByRole("button", { name: t, exact: true });
		await page.goto(`${base}/books/`);
		await page.waitForSelector("astro-island:not([ssr]) #reading-guide");
		assert.equal(await hub.locator("article").count(), 48);
		await hub.getByRole("button", { name: /加载更多/ }).click();
		assert.equal(await hub.locator("article").count(), 96);
		if (width === 1440) {
			while (await hub.getByRole("button", { name: /加载更多/ }).count())
				await hub.getByRole("button", { name: /加载更多/ }).click();
			const targets = await hub
				.locator("article h3 a")
				.evaluateAll((els) => els.map((a) => a.getAttribute("href")));
			assert.equal(new Set(targets).size, works.size);
			assert.equal(targets.length, works.size);
			for (const d of new Set(records.flatMap((b) => b.domains ?? []))) {
				await filter(d).click();
				const tagged = records.filter((b) => b.domains?.includes(d));
				const ids = new Set(tagged.map((b) => b.slug));
				const expected = [
					...new Set(
						tagged.map((b) =>
							b.listedWith && ids.has(b.listedWith) ? b.listedWith : b.slug,
						),
					),
				].sort();
				while (await hub.getByRole("button", { name: /加载更多/ }).count())
					await hub.getByRole("button", { name: /加载更多/ }).click();
				const actual = await hub
					.locator("article h3 a")
					.evaluateAll((els) =>
						els.map((a) => a.pathname.split("/").filter(Boolean).at(-1)).sort(),
					);
				assert.deepEqual(actual, expected, d);
			}
		}
		await hub.getByRole("button", { name: /^全部 / }).click();
		for (const [term, count] of [
			["进化心理学", 1],
			["透过地理看历史", 1],
			["经济学原理", 2],
			["男人来自火星", 2],
		]) {
			await search.fill(term);
			assert.equal(
				await hub.locator("article h3 a").filter({ hasText: term }).count(),
				count,
				term,
			);
		}
		await search.fill("进化心理学（第2版）");
		await hub
			.locator("h3 a")
			.filter({ hasText: "进化心理学（第2版）" })
			.click();
		const related = page.getByRole("navigation", { name: "同书版本或收录" });
		await related.getByRole("link", { name: "进化心理学（第4版）" }).click();
		await page
			.locator("#book-overview-heading")
			.filter({ hasText: "第4版" })
			.waitFor();
		await page.goto(`${base}/books/`);
		await page.waitForSelector("astro-island:not([ssr]) #reading-guide");
		assert.equal(
			await hub.locator(".description .cue").first().innerText(),
			"概述",
		);
		assert.equal(
			await hub.locator(".question .cue").first().innerText(),
			"问题",
		);
		for (const name of ["心理学", "经济学"]) {
			await filter(name).click();
			await search.fill("稀缺");
			const b = hub.getByRole("heading", { name: "稀缺", exact: true });
			await b.waitFor();
			assert.equal(await b.count(), 1);
			assert.equal(new URL(page.url()).searchParams.get("domain"), name);
		}
		await page.reload();
		await hub.getByRole("heading", { name: "稀缺", exact: true }).waitFor();
		await hub
			.locator("article h3 a")
			.filter({ hasText: /^稀缺$/ })
			.click();
		await page.waitForSelector("#book-overview-heading");
		assert.equal(await page.locator("#public-question").innerText(), "问题");
		assert.ok(
			(await page
				.locator("section[aria-labelledby=public-question] a")
				.count()) >= 2,
		);
		await page.goBack();
		await hub.getByRole("heading", { name: "稀缺", exact: true }).waitFor();
		assert.equal(await search.inputValue(), "稀缺");
		await search.fill("no-such-book-xyz");
		await hub.getByText(/没有匹配的书籍/).waitFor();
		await hub.getByRole("button", { name: "清除筛选" }).click();
		await filter("生物学").click();
		await page.waitForFunction(
			() =>
				Number(
					getComputedStyle(document.querySelector("#content-wrapper")).opacity,
				) > 0.99,
		);
		assert.ok(
			await page.evaluate(
				() => document.documentElement.scrollWidth <= innerWidth,
			),
		);
		await page.screenshot({
			path: `${out}domains-${width}.png`,
			animations: "disabled",
		});
		await page.goto(`${base}/books/?shelf=psychology&status=reading&q=象`);
		await hub
			.getByRole("heading", { name: "象与骑象人：幸福的假设", exact: true })
			.waitFor();
		assert.equal(await hub.locator("article").count(), 1);
		assert.deepEqual(errors, []);
		await page.close();
		console.log(
			`${width}: cross-domain, search, history, citations, legacy links OK`,
		);
	}
} finally {
	await browser.close();
}
