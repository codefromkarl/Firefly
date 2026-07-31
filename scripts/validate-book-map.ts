import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const rawArgs = process.argv.slice(2);
const args = rawArgs[0] === "--" ? rawArgs.slice(1) : rawArgs;
const [slug, ...extraArgs] = args;
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

if (!slug || extraArgs.length > 0 || !slugPattern.test(slug)) {
	console.error("Usage: pnpm validate:book-map -- <kebab-case-book-slug>");
	process.exit(1);
}

const booksRoot = path.resolve("src/content/books");
const bookDirectory = path.resolve(booksRoot, slug);
if (!bookDirectory.startsWith(`${booksRoot}${path.sep}`)) {
	console.error(`Unsafe book slug: ${slug}`);
	process.exit(1);
}

const indexPath = path.join(bookDirectory, "index.md");
const graphPath = path.join(bookDirectory, "graph.json");
for (const requiredPath of [indexPath, graphPath]) {
	if (!fs.existsSync(requiredPath) || !fs.statSync(requiredPath).isFile()) {
		console.error(`Missing required book-map file: ${requiredPath}`);
		process.exit(1);
	}
}

let graphBook: unknown;
try {
	const graph = JSON.parse(fs.readFileSync(graphPath, "utf8")) as {
		book?: unknown;
	};
	graphBook = graph.book;
} catch (error) {
	console.error(`Unable to parse ${graphPath}:`, error);
	process.exit(1);
}

if (graphBook !== slug) {
	console.error(
		`Graph reference must match its directory slug: expected "${slug}", received ${JSON.stringify(graphBook)}`,
	);
	process.exit(1);
}

const sync = spawnSync("pnpm", ["exec", "astro", "sync"], {
	cwd: process.cwd(),
	encoding: "utf8",
	stdio: "inherit",
});
if (sync.error) {
	console.error("Unable to start Astro content validation:", sync.error);
	process.exit(1);
}
if (sync.status !== 0) process.exit(sync.status ?? 1);

console.log(`Validated book-map content for "${slug}".`);
