import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { validateVault } from "./creator-validate.mjs";

function fixture(t, files) {
	const root = fs.mkdtempSync(path.join(os.tmpdir(), "creator-reference-"));
	t.after(() => fs.rmSync(root, { recursive: true, force: true }));
	for (const [name, text] of Object.entries(files)) {
		fs.mkdirSync(path.dirname(path.join(root, name)), { recursive: true });
		fs.writeFileSync(path.join(root, name), text);
	}
	return root;
}

test("valid source links still report unreviewed editorial content", (t) => {
	const root = fixture(t, {
		"50 来源/source.md":
			"---\nid: S1\ntype: source\nverification: text_checked\nlocator: Chapter 7\n---\n",
		"20 知识卡片/claim.md":
			"---\nid: C1\ntype: claim\nverification: pending_review\nsources:\n  - '[[50 来源/source]]'\n---\n[[50 来源/source]]",
	});
	const result = validateVault(root);
	assert.deepEqual(result.errors, []);
	assert.equal(result.warnings.length, 1);
	fs.renameSync(
		path.join(root, "50 来源/source.md"),
		path.join(root, "50 来源/moved.md"),
	);
	assert.ok(
		validateVault(root).errors.some((error) =>
			error.includes("unresolved sources"),
		),
	);
});

test("candidate references cannot be mistaken for checked source text", (t) => {
	const root = fixture(t, {
		"candidate.md":
			"---\nid: S1\ntype: source\nsource_type: book_candidate\nverification: text_checked\nreading_status: unread\nurl: https://example.org/book\n---\n",
		"claim.md":
			"---\nid: C1\ntype: claim\nverification: reviewed\nsources: ['[[candidate]]']\n---\n",
	});
	const result = validateVault(root);
	assert.ok(result.errors.some((error) => error.includes("candidate book")));
	assert.ok(result.errors.some((error) => error.includes("reviewed_by")));
});

test("ambiguous links and duplicate ids fail, template placeholders are ignored", (t) => {
	const root = fixture(t, {
		"a/source.md": "---\nid: SAME\n---\n",
		"b/source.md": "---\nid: SAME\n---\n",
		"note.md": "[[source]]\n",
		"90 模板/claim.md": "[[UNFILLED]]\n",
	});
	const result = validateVault(root);
	assert.equal(result.errors.length, 2);
	assert.ok(result.errors.some((error) => error.includes("duplicate id")));
	assert.ok(
		result.errors.some((error) => error.includes("unresolved body link")),
	);
});
