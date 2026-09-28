import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import matter from "gray-matter";

/** Check references, not whether an author's conclusion is true. */
export function validateVault(vaultPath) {
	const root = fs.realpathSync(vaultPath);
	const errors = [];
	const warnings = [];
	const notes = [];
	function walk(directory) {
		for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
			if (entry.name.startsWith(".") || entry.isSymbolicLink()) continue;
			const absolute = path.join(directory, entry.name);
			if (entry.isDirectory()) {
				if (entry.name !== "90 模板") walk(absolute);
			} else if (entry.name.endsWith(".md")) {
				try {
					const parsed = matter(fs.readFileSync(absolute, "utf8"));
					notes.push({
						...parsed,
						relative: path.relative(root, absolute).split(path.sep).join("/"),
					});
				} catch (error) {
					errors.push(`${path.relative(root, absolute)}: ${error.message}`);
				}
			}
		}
	}
	walk(root);
	const paths = new Map(
		notes.map((note) => [note.relative.replace(/\.md$/, ""), note]),
	);
	const ids = new Map();
	const books = new Set(
		notes
			.filter((note) => note.data.type === "book")
			.map((note) => note.data.book_id),
	);
	function resolve(reference, owner) {
		const match =
			typeof reference === "string" && reference.match(/^\[\[([^\]]+)\]\]$/);
		if (!match) return undefined;
		const target = match[1].split("|")[0].split("#")[0].replace(/\.md$/, "");
		if (target.startsWith("/") || target.split("/").includes(".."))
			return undefined;
		if (!target) return owner;
		if (paths.has(target)) return paths.get(target);
		if (target.endsWith(".base")) {
			const base = path.join(root, target);
			if (fs.existsSync(base) && fs.lstatSync(base).isFile())
				return { data: { type: "base" } };
		}
		const sibling = path.posix.join(path.posix.dirname(owner.relative), target);
		if (paths.has(sibling)) return paths.get(sibling);
		const matches = notes.filter(
			(note) => path.posix.basename(note.relative, ".md") === target,
		);
		return matches.length === 1 ? matches[0] : undefined;
	}
	for (const note of notes) {
		const { data, relative } = note;
		const fail = (message) => errors.push(`${relative}: ${message}`);
		if (data.id) {
			if (ids.has(data.id))
				fail(`duplicate id ${data.id}: ${ids.get(data.id)}`);
			ids.set(data.id, relative);
		}
		if (
			["source", "claim", "topic", "project", "article"].includes(data.type) &&
			!data.id
		)
			fail("missing stable id");
		if (data.type === "source") {
			if (data.book_id && !books.has(data.book_id))
				fail(`unknown catalogue book_id: ${data.book_id}`);
			if (
				!["text_checked", "metadata_only", "pending"].includes(
					data.verification,
				)
			)
				fail("invalid source verification");
			if (!data.locator && !data.url) fail("missing source locator or URL");
			if (data.url) {
				try {
					if (!["http:", "https:"].includes(new URL(data.url).protocol))
						fail("source URL must be public HTTP(S)");
				} catch {
					fail("invalid source URL");
				}
			}
			if (
				data.source_type === "book_candidate" &&
				(data.verification === "text_checked" ||
					data.reading_status !== "unread")
			)
				fail("candidate book must stay unread and cannot claim checked text");
		}
		for (const field of ["sources", "topics", "claims"]) {
			// Imported catalogue topics are labels; research topics are note links.
			if (data.type === "book" && field === "topics") continue;
			if (data[field] === undefined) continue;
			if (!Array.isArray(data[field])) {
				fail(`${field} must be a list`);
				continue;
			}
			for (const reference of data[field]) {
				const target = resolve(reference, note);
				if (!target) {
					fail(`unresolved ${field}: ${reference}`);
					continue;
				}
				const expected = {
					sources: "source",
					topics: "topic",
					claims: "claim",
				}[field];
				if (target.data.type !== expected)
					fail(
						`${field} points to ${target.data.type ?? "untyped note"}: ${reference}`,
					);
				if (
					field === "sources" &&
					["claim", "article"].includes(data.type) &&
					target.data.verification !== "text_checked"
				) {
					warnings.push(
						`${relative}: ${reference} is ${target.data.verification}; cannot treat it as verified support`,
					);
				}
			}
		}
		if (
			data.type === "claim" &&
			(!Array.isArray(data.sources) || !data.sources.length) &&
			data.claim_type !== "editorial_inference"
		)
			fail("sourced claim needs at least one source");
		if (["claim", "article"].includes(data.type)) {
			if (!["pending_review", "reviewed"].includes(data.verification))
				fail("invalid editorial verification");
			if (data.verification === "pending_review")
				warnings.push(`${relative}: awaiting editorial review`);
			if (
				data.verification === "reviewed" &&
				(!data.reviewed_by || !data.reviewed_at)
			)
				fail("reviewed content needs reviewed_by and reviewed_at");
		}
		const body = note.content.replace(/```[\s\S]*?```/g, "");
		for (const match of body.matchAll(/(?<!!)\[\[[^\]]+\]\]/g)) {
			if (!resolve(match[0], note)) fail(`unresolved body link: ${match[0]}`);
		}
	}
	return {
		vault: root,
		notes: notes.length,
		errors,
		warnings,
		meaning:
			"Reference integrity only; not factual verification, user approval or publication.",
	};
}

if (
	process.argv[1] &&
	path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
	const args = process.argv.slice(2);
	if (args.length !== 2 || args[0] !== "--vault") {
		console.error(
			"Usage: node scripts/creator-validate.mjs --vault <directory>",
		);
		process.exitCode = 2;
	} else {
		try {
			const report = validateVault(args[1]);
			console.log(JSON.stringify(report, null, 2));
			process.exitCode = report.errors.length ? 1 : 0;
		} catch (error) {
			console.error(error.message);
			process.exitCode = 1;
		}
	}
}
