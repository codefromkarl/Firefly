from pathlib import Path
import tempfile
import unittest

from creator_system.store import Store, ControlError
from creator_system.sources import register_source, create_evidence, list_units, replay_evidence, withdraw_source
from creator_system.recovery import recover_source
from creator_system.workflow import Workflow


class RecoveryTests(unittest.TestCase):
    def test_missing_source_recovered_without_changing_identity_or_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            original = root / "source.txt"
            original.write_text("Synthetic recovery text.")
            version = register_source(store, original, "S")
            evidence = create_evidence(store, version["id"], list_units(store, version["id"])[0]["locator"])
            workflow = Workflow(store)
            workflow.create_project("P", "Recovery", {"read_paths": ["."], "write_paths": ["."], "tools": [], "network": False})
            claim = workflow.register_claim("P", "C", "quotation", "Synthetic recovery text.", [{"evidence_id": evidence["id"], "relation": "supports"}])
            original.unlink()
            self.assertFalse(workflow.inspect("claim", claim["id"])["valid"])
            result = recover_source(store, version["id"])
            self.assertFalse(original.exists())
            self.assertEqual(Path(result["path"]).read_text(), "Synthetic recovery text.")
            self.assertFalse(result["status"]["current_source_unavailable"])
            self.assertTrue(workflow.inspect("claim", claim["id"])["valid"])
            self.assertEqual(recover_source(store, version["id"])["receipt"]["id"], result["receipt"]["id"])
            self.assertEqual(len(store.list("source_version")), 1)
            # Recovered user copy is not a hardlink to the immutable source blob.
            Path(result["path"]).write_text("edited recovery copy")
            self.assertTrue(replay_evidence(store, evidence["id"])["valid"])

    def test_recovering_old_or_withdrawn_source_never_reactivates_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            path = root / "source.txt"
            path.write_text("old")
            old = register_source(store, path, "S")
            path.write_text("new")
            current = register_source(store, path, "S")
            withdraw_source(store, "S", "requires investigation")
            result = recover_source(store, old["id"])
            self.assertTrue(result["status"]["withdrawn"])
            self.assertTrue(result["status"]["active_version_changed"])
            self.assertTrue(result["status"]["current_source_changed"])
            self.assertEqual(store.get("source", "S")["data"]["active_version_id"], current["id"])

    def test_existing_or_escaping_recovery_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            path = root / "source.txt"
            path.write_text("source")
            version = register_source(store, path, "S")
            existing = store.vault / "my-note.md"
            existing.write_text("user text")
            with self.assertRaises(ControlError):
                recover_source(store, version["id"], "my-note.md")
            with self.assertRaises(ControlError):
                recover_source(store, version["id"], "../escaped.txt")
            self.assertEqual(existing.read_text(), "user text")
