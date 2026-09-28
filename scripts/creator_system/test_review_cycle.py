import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from creator_system import test_editorial as fixtures
from creator_system.editorial import record_action
from creator_system.store import Store, ControlError
from creator_system.workflow import Workflow
from creator_system.workbench import write_dashboard
from creator_system.integrity import audit_database
from creator_system.backup import backup_vault, restore_backup


class ReviewCycleTests(unittest.TestCase):
    setUp = fixtures.EditorialTests.setUp
    tearDown = fixtures.EditorialTests.tearDown
    analysis_for = fixtures.EditorialTests.analysis_for
    review_for = fixtures.EditorialTests.review_for
    imported = fixtures.EditorialTests.imported

    def revision(self, identity, parent=None, filename="revised.md"):
        (self.root / filename).write_text(self.path.read_text().replace("First actual sentence.", "Revised actual sentence."))
        return self.flow.register_draft("P", filename, ["C"], [{"paragraph": 2, "claim_ids": ["C"]}], identity, parent)

    def test_actions_preserve_objections_idempotency_and_changed_intent(self):
        review_id = self.imported()["review_ids"][0]
        args = (self.store, "D", "retain", "Synthetic rationale", "Synthetic editor")
        first = record_action(*args, finding_id="F-1")
        self.assertEqual(first, record_action(*args, finding_id="F-1"))
        record_action(self.store, "D", "defer", "Need material", "Synthetic editor", review_id=review_id)
        back = record_action(*args, finding_id="F-1")
        self.assertNotEqual(first["id"], back["id"])
        self.assertEqual(len(self.store.list("review_action")), 3)
        self.assertFalse(back["data"]["author_approved"])
        self.assertFalse(back["data"]["resolves_review"])
        self.assertIn(review_id, [r["id"] for r in self.flow._outstanding_reviews([("draft", "D")])])
        write_dashboard(self.store)
        self.assertIn("保留原文（待复查）", (self.root / "系统首页.md").read_text())

    def test_candidate_snapshot_and_current_action_staleness(self):
        self.imported()
        candidate = self.root / "candidate.md"
        candidate.write_text("# Revised candidate\n\nPrivate synthetic proposal.")
        original = self.path.read_bytes()
        action = record_action(self.store, "D", "revise", "Test candidate", "Synthetic editor", finding_id="F-1", candidate_path="candidate.md")
        blob = action["data"]["candidate_blob"]
        candidate.write_text("Author edited the candidate")
        self.assertFalse(self.flow.inspect("review_action", action["id"])["valid"])
        self.assertIn(b"Private synthetic", self.store.read_blob(blob))
        self.assertEqual(self.path.read_bytes(), original)
        write_dashboard(self.store)
        self.assertIn("材料已变化", (self.root / "系统首页.md").read_text())
        (self.store.objects / blob).unlink()
        with self.assertRaises(ControlError):
            audit_database(self.store.db, self.store.read_blob)

    def test_new_draft_inherits_open_reviews_and_needs_its_own_recheck(self):
        review_id = self.imported()["review_ids"][0]
        record_action(self.store, "D", "defer", "Old draft only", "Synthetic editor", finding_id="F-1")
        self.path.write_text(self.path.read_text() + "\nA new paragraph.\n")
        draft = self.revision("D2")
        self.assertEqual(draft["data"]["parent_draft_id"], "D")
        self.assertEqual(draft["data"]["inherited_reviews"][0]["id"], review_id)
        green = self.flow.record_review("draft", "D2", [{"name": "New general check", "passed": True}], conclusion="pass")
        with self.assertRaisesRegex(ControlError, "Unresolved review"):
            self.flow.prepare_release("P", "D2", "output", [green["id"]])
        write_dashboard(self.store)
        text = (self.root / "系统首页.md").read_text()
        self.assertIn("旧稿 D 第", text)
        self.assertIn("Revised", (self.root / "revised.md").read_text())
        self.assertNotIn("Old draft only", text)
        checks = [{**check, "passed": True} for check in self.store.get("review", review_id)["data"]["checks"]]
        self.flow.record_review("draft", "D2", checks, conclusion="pass", supersedes=[review_id])
        self.assertEqual(self.flow._outstanding_reviews([("draft", "D2")]), [])
        self.revision("BRANCH", "D", "branch.md")
        self.assertIn(review_id, [r["id"] for r in self.flow._outstanding_reviews([("draft", "BRANCH")])])
        self.revision("D3", "D2", "third.md")
        self.assertEqual(self.flow.project_status("P")["status"], "awaiting_review")

    def test_cross_project_and_resolved_review_actions_are_rejected(self):
        review_id = self.imported()["review_ids"][0]
        for invalid in ("", False):
            with self.assertRaisesRegex(ControlError, "Parent draft"):
                self.flow.register_draft("P", "draft.md", [], [], "INVALID", invalid)
        self.flow.create_project("OTHER", "Another project", {"read_paths": ["."], "write_paths": ["."], "tools": [], "network": False})
        with self.assertRaisesRegex(ControlError, "another project"):
            self.flow.register_draft("OTHER", "draft.md", [], [], "OTHER-D", "D")
        self.flow.register_draft("OTHER", "draft.md", [], [], "OTHER-D")
        with self.assertRaises(ControlError):
            record_action(self.store, "OTHER-D", "retain", "Cannot borrow", "Synthetic", review_id=review_id)
        checks = [{**check, "passed": True} for check in self.store.get("review", review_id)["data"]["checks"]]
        self.flow.record_review("draft", "D", checks, conclusion="pass", supersedes=[review_id])
        with self.assertRaises(ControlError):
            record_action(self.store, "D", "defer", "Already resolved", "Synthetic", review_id=review_id)

    def test_real_cli_action_and_backup_restore(self):
        review_id = self.imported()["review_ids"][0]
        self.revision("D2")
        (self.root / "candidate.md").write_text("# Synthetic candidate\n\nChanged paragraph")
        cli = Path(__file__).resolve().parents[1] / "creator-system.py"
        proc = subprocess.run([sys.executable, "-B", str(cli), "--vault", str(self.root), "review-action", "--draft", "D2",
                               "--finding", "F-1", "--action", "revise", "--reason", "Synthetic CLI check", "--actor", "Synthetic",
                               "--candidate", "candidate.md"], text=True, capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        action = json.loads(proc.stdout)["action"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = backup_vault(self.store, root / "backups")["data"]["path"]
            restore_backup(archive, root / "restored")
            restored = Store(root / "restored")
            try:
                self.assertTrue(Workflow(restored).inspect("review_action", action["id"])["valid"])
                self.assertIn(review_id, [r["id"] for r in Workflow(restored)._outstanding_reviews([("draft", "D2")])])
                self.assertGreater(audit_database(restored.db, restored.read_blob)["records"], 5)
            finally:
                restored.close()
