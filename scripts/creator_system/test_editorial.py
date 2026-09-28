import json
import unittest
from creator_system import test_semantic as semantic_fixtures
from creator_system import test_workflow as workflow_fixtures
from creator_system.store import Store, ControlError
from creator_system.workflow import Workflow
from creator_system.editorial import import_review, draft_impact, map_anchors
from creator_system.workbench import write_dashboard
from creator_system.integrity import audit_database


class EditorialTests(unittest.TestCase):
    analysis_for = semantic_fixtures.SemanticTests.analysis_for
    review_for = semantic_fixtures.SemanticTests.review_for

    def setUp(self):
        semantic_fixtures.SemanticTests.setUp(self)
        self.store = Store(self.root)
        self.flow = Workflow(self.store)
        self.flow.create_project("P", "Synthetic editorial test", {"read_paths": ["."], "write_paths": ["."], "tools": [], "network": False})
        self.flow.register_claim("P", "C", "personal_judgment", "Synthetic opinion only", [])
        self.flow.register_draft("P", "draft.md", ["C"], [{"paragraph": 2, "claim_ids": ["C"]}], "D")
        for name, data in [("packet", self.pack), ("analysis", self.analysis), ("review", self.review_for())]:
            (self.root / f"{name}.json").write_text(json.dumps(data))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def imported(self):
        return import_review(self.store, "D", "packet.json", "analysis.json", "review.json")

    def test_import_idempotency_dashboard_and_objection_blocks_release(self):
        result = self.imported()
        self.assertEqual(result, self.imported())
        review = self.store.get("review", result["review_ids"][0])
        self.assertEqual(review["data"]["findings"][0]["mapped_anchors"][0]["paragraph"], 2)
        green = self.flow.record_review("draft", "D", [{"name": "another check", "passed": True}], conclusion="pass")
        with self.assertRaisesRegex(ControlError, "Unresolved review"):
            self.flow.prepare_release("P", "D", "output", [green["id"]])
        write_dashboard(self.store)
        text = (self.root / "系统首页.md").read_text()
        for phrase in ["Need original context", "First actual sentence.", "Attach the actual original passage", "Scope remains uncertain"]:
            self.assertIn(phrase, text)
        self.assertGreater(audit_database(self.store.db, self.store.read_blob)["referenced_blobs"], 3)
        fingerprint = review["data"]["attachments"]["analysis"]
        (self.store.objects / fingerprint).unlink()
        self.assertFalse(self.flow.inspect("review", review["id"])["valid"])
        with self.assertRaises(ControlError):
            audit_database(self.store.db, self.store.read_blob)

    def test_source_change_invalidates_review_and_reimport(self):
        review_id = self.imported()["review_ids"][0]
        self.source.write_text(self.source.read_text() + "Changed source note")
        self.assertFalse(self.flow.inspect("review", review_id)["valid"])
        with self.assertRaisesRegex(ControlError, "stale"):
            self.imported()
        self.assertIn(review_id, [r["id"] for r in self.flow._outstanding_reviews([("draft", "D")])])
        earlier = self.store.get("review", review_id)["data"]
        self.flow.record_review("draft", "D", [{"name": earlier["checks"][0]["name"], "passed": True}],
                                conclusion="pass", supersedes=[review_id], context_paths=["source.md"])
        self.assertNotIn(review_id, [r["id"] for r in self.flow._outstanding_reviews([("draft", "D")])])

    def test_changed_draft_invalidates_old_review_but_unchanged_paragraph_maps(self):
        review_id = self.imported()["review_ids"][0]
        self.path.write_text(self.path.read_text().replace("First actual", "Inserted new paragraph.\n\nFirst actual"))
        result = draft_impact(self.store, "D", "draft.md", review_id)
        self.assertFalse(self.flow.inspect("review", review_id)["valid"])
        self.assertEqual(result["claim_mapping_candidates"][0]["paragraph"], 3)
        self.assertTrue(result["new_unassigned_blocks"])
        self.assertFalse(result["review_reused"])

    def test_duplicate_anchor_and_wrong_draft_refused_without_review_writes(self):
        text = self.path.read_text() + "\nFirst actual sentence.\n"
        with self.assertRaisesRegex(ControlError, "Ambiguous"):
            map_anchors(text, self.pack, self.review_for()["findings"][0])
        self.path.write_text(self.path.read_text() + "Changed")
        with self.assertRaises(ControlError):
            self.imported()
        self.assertEqual(self.store.list("review"), [])


class PreviewSelectionTests(unittest.TestCase):
    setUp = workflow_fixtures.WorkflowTests.setUp
    tearDown = workflow_fixtures.WorkflowTests.tearDown
    review = workflow_fixtures.WorkflowTests.review
    release = workflow_fixtures.WorkflowTests.release

    def test_success_only_selection_and_concurrent_conflict(self):
        self.release()
        first = self.flow.record_preview("D1", "output")
        selected = self.store.get("selection", "P1")
        with self.assertRaisesRegex(ControlError, "concurrently"):
            self.flow.record_preview("D1", "output", None)
        (self.vault / "output/title.txt").write_text("Manual edit")
        with self.assertRaises(ControlError):
            self.flow.record_preview("D1", "output", selected["digest"])
        self.assertEqual(self.store.get("selection", "P1"), selected)
        self.assertFalse(self.flow.inspect("preview", first["preview_id"])["valid"])

    def test_dashboard_link_and_manual_edits_preserved(self):
        self.release()
        self.flow.record_preview("D1", "output")
        write_dashboard(self.store)
        target = self.vault / "系统首页.md"
        self.assertIn((self.vault / "output/bilibili.html").as_uri(), target.read_text())
        target.write_text("My manual note")
        with self.assertRaises(ControlError):
            write_dashboard(self.store)
        self.assertEqual(target.read_text(), "My manual note")
