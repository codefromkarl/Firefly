import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(
	new URL("./import-book-library.ts", import.meta.url),
);

test("explicit import manifest validates the entire list and rejects a source outside the library", async () => {
	const root = await mkdtemp(join(tmpdir(), "firefly-import-test-"));
	const leaf = await mkdtemp(join(root, "library-"));
	try {
		await writeFile(join(leaf, "test.txt"), "local fixture");
		await writeFile(join(root, "outside.txt"), "must not be published");
		const file = join(root, "plan.json");
		const book = {
			title: "清单校验自测示例",
			authors: ["测试作者"],
			description: "只用于测试书目清单。",
			shelf: "reference",
			file: "test.txt",
		};
		await writeFile(
			file,
			JSON.stringify([
				book,
				{ ...book, title: "禁止越界的书目", file: "../outside.txt" },
			]),
		);
		const result = spawnSync(
			process.execPath,
			[
				"--import",
				"tsx",
				script,
				"--manifest",
				file,
				"--source",
				leaf,
				"--apply",
			],
			{
				encoding: "utf8",
				timeout: 15_000,
			},
		);
		assert.equal(result.status, 1, result.error?.message);
		assert.match(result.stderr, /书籍文件不在指定书单目录/);
		assert.equal(result.stdout.trim(), "");
	} finally {
		await rm(root, { recursive: true, force: true });
	}
});
