from pathlib import Path
import tempfile
import unittest
from creator_system.store import Store, ControlError
from creator_system.sources import register_source, search, withdraw_source
from creator_system.workflow import Workflow


class SourceLifecycleTests(unittest.TestCase):
    def test_recorded_web_failure_invalidates_review_but_preserves_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "vault")
            self.addCleanup(store.close)
            source = Path(tmp) / "page.txt"
            source.write_text("synthetic source")
            version = register_source(store, source, "WEB", url="https://example.com/article")
            workflow = Workflow(store)
            workflow.create_project("P", "test", {"read_paths": ["."], "write_paths": ["."], "tools": [], "network": False})
            snapshot = workflow.snapshot("P", records=[{"kind": "source_version", "id": version["id"]}])
            self.assertEqual(workflow._snapshot_issues(snapshot), [])
            store.create("receipt", {"type": "web_check", "source_id": "WEB", "source_version_id": version["id"],
                                     "status": "unavailable", "checked_at": "2026-09-22T00:00:00+00:00"})
            self.assertTrue(workflow._snapshot_issues(snapshot))
            self.assertEqual(store.read_blob(version["data"]["snapshot_sha256"]), b"synthetic source")

    def test_default_search_excludes_history_and_withdrawn_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "vault")
            self.addCleanup(store.close)
            source = Path(tmp) / "book.txt"
            source.write_text("needle old")
            old = register_source(store, source, "S")
            source.write_text("needle new")
            current = register_source(store, source, "S")
            self.assertEqual([r["source_version_id"] for r in search(store, "needle")], [current["id"]])
            historical = search(store, "needle", source_version_id=old["id"])
            self.assertTrue(historical[0]["source_state"]["active_version_changed"])
            withdraw_source(store, "S", "superseded")
            self.assertEqual(search(store, "needle"), [])
            self.assertTrue(search(store, "needle", source_version_id=old["id"])[0]["source_state"]["withdrawn"])

    def test_rejected_registration_does_not_create_orphan_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "vault")
            self.addCleanup(store.close)
            source = Path(tmp) / "book.txt"
            source.write_text("first")
            register_source(store, source, "S", work_id="W1")
            source.write_text("changed")
            with self.assertRaises(ControlError):
                register_source(store, source, "S", work_id="W2")
            self.assertEqual(len(store.list("source_version")), 1)
            withdraw_source(store, "S", "withdraw")
            with self.assertRaises(ControlError):
                register_source(store, source, "S")
            self.assertEqual(len(store.list("source_version")), 1)
