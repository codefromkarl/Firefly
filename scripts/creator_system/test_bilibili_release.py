"""Real exporter integration using synthetic content only."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from creator_system.store import ControlError, digest
from creator_system import test_workflow as fixtures


class BilibiliReleaseTests(unittest.TestCase):
    setUp = fixtures.WorkflowTests.setUp
    tearDown = fixtures.WorkflowTests.tearDown
    review = fixtures.WorkflowTests.review
    fixture_approve = fixtures.WorkflowTests.fixture_approve

    def test_controlled_cli_rejects_removed_format_and_enforces_asset_scope(self):
        self.package()
        cli = Path(__file__).resolve().parents[1] / "creator-system.py"
        def preview(*args):
            return subprocess.run([sys.executable, "-B", str(cli), "--vault", str(self.vault), "preview", "--draft", "D1", *args],
                                  capture_output=True, text=True, timeout=30)
        result = preview("--assets", "notes/assets.json", "--output", "output/controlled")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["format"], "bilibili")
        self.assertEqual(json.loads(result.stdout)["preview"]["images"], 1)
        generic = preview("--format", "generic", "--output", "output/generic")
        self.assertNotEqual(generic.returncode, 0)
        self.assertIn("unrecognized arguments", generic.stderr)
        self.assertFalse((self.vault / "output/generic").exists())
        self.assertNotEqual(preview("--assets", "output/asset-order.json", "--output", "output/denied").returncode, 0)
        self.assertFalse((self.vault / "output/denied").exists())
        self.assertNotEqual(preview("--format", "generic", "--assets", "notes/assets.json").returncode, 0)

    def package(self):
        project = Path(__file__).resolve().parents[2]
        image = self.vault / "notes/picture.png"
        result = subprocess.run(["node", "--input-type=module", "-e",
                                 "import sharp from 'sharp'; await sharp({create:{width:4,height:4,channels:3,background:'#ffffff'}}).png().toFile(process.argv[1]);",
                                 str(image)], cwd=project, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        assets = self.vault / "notes/assets.json"
        assets.write_text(json.dumps({"schema": 1, "images": [{"id": "sample", "path": "picture.png", "caption": "Synthetic picture"}]}))
        result = subprocess.run(["node", str(project / "scripts/creator_system/bilibili-render.mjs"), "--input", str(self.vault / "notes/draft.md"),
                                 "--assets", str(assets), "--output", str(self.vault / "output")], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.vault / "output"

    def test_exact_package_and_decision_invalidated_by_any_delivered_file_change(self):
        folder = self.package()
        release = self.flow.prepare_release("P1", "D1", "output", [self.review()["id"]])
        self.assertEqual(release["data"]["format"], "bilibili")
        image = json.loads((folder / "asset-order.json").read_text())["images"][0]["file"]
        self.assertIn(image, release["data"]["artifacts"])
        decision = self.fixture_approve(release)
        for name in ["title.txt", "bilibili.html", "bilibili.txt", "asset-order.json", image, ".creator-bilibili.json"]:
            with self.subTest(name=name):
                target = folder / name
                original = target.read_bytes()
                target.write_bytes(original + b"changed")
                self.assertFalse(self.flow.inspect("release", release["id"])["valid"])
                self.assertFalse(self.flow.inspect("decision", decision["id"])["valid"])
                with self.assertRaises(ControlError):
                    self.flow.request_delivery(release["id"], "synthetic", "only-record-no-network")
                self.assertEqual(self.store.read_blob(release["data"]["artifacts"][name]["sha256"]), original)
                target.write_bytes(original)
        self.assertTrue(self.flow.inspect("release", release["id"])["valid"])
        (folder / image).unlink()
        self.assertFalse(self.flow.inspect("release", release["id"])["valid"])

    def test_missing_image_and_same_body_different_private_revision_rejected(self):
        folder = self.package()
        review = self.review()
        image = folder / json.loads((folder / "asset-order.json").read_text())["images"][0]["file"]
        original = image.read_bytes()
        image.unlink()
        with self.assertRaises(OSError):
            self.flow.prepare_release("P1", "D1", "output", [review["id"]])
        image.write_bytes(original)
        note = self.vault / "notes/draft.md"
        note.write_text("---\nprivate: changed\n---\n\n" + note.read_text())
        self.flow.register_draft("P1", "notes/draft.md", ["C1"], [{"paragraph": 2, "claim_ids": ["C1"]}], "D2")
        new_review = self.flow.record_review("draft", "D2", [{"name": "synthetic", "passed": True}], conclusion="pass")
        with self.assertRaisesRegex(ControlError, "exact registered draft"):
            self.flow.prepare_release("P1", "D2", "output", [new_review["id"]])

    def test_current_image_list_controls_release_and_hashes_must_agree(self):
        folder = self.package()
        marker_path = folder / ".creator-bilibili.json"
        marker = json.loads(marker_path.read_text())
        (folder / "images/unused.png").write_bytes(b"old unused file")
        marker["hashes"]["images/unused.png"] = digest(b"old unused file")
        marker_path.write_text(json.dumps(marker))
        review = self.review()
        release = self.flow.prepare_release("P1", "D1", "output", [review["id"]])
        self.assertNotIn("images/unused.png", release["data"]["artifacts"])
        order_path = folder / "asset-order.json"
        order = json.loads(order_path.read_text())
        order["images"][0]["sha256"] = "0" * 64
        order_path.write_text(json.dumps(order))
        marker["hashes"]["asset-order.json"] = digest(order_path.read_bytes())
        marker_path.write_text(json.dumps(marker))
        with self.assertRaisesRegex(ControlError, "order hash"):
            self.flow.prepare_release("P1", "D1", "output", [review["id"]])

    def test_old_packages_and_historical_generic_releases_cannot_be_delivered(self):
        folder = self.package()
        review = self.review()
        release = self.flow.prepare_release("P1", "D1", "output", [review["id"]])
        legacy = self.store.create("release", {**release["data"], "format": "generic"})
        self.assertFalse(self.flow.inspect("release", legacy["id"])["valid"])
        with self.assertRaises(ControlError):
            self.fixture_approve(legacy)
        (folder / ".creator-bilibili.json").unlink()
        (folder / ".creator-export.json").write_text('{"tool":"firefly-creator-export","version":1}')
        with self.assertRaisesRegex(ControlError, "Bilibili package required"):
            self.flow.prepare_release("P1", "D1", "output", [review["id"]])


if __name__ == "__main__":
    unittest.main()
