import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from creator_system.store import Store, ControlError
from creator_system.backup import backup_vault, restore_backup, verify_backup
from creator_system.sources import register_source, create_evidence, list_units
from creator_system.workflow import Workflow


class BackupTests(unittest.TestCase):
    def test_backup_and_restore_cannot_put_private_data_in_public_project_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            archive = backup_vault(store, root / "backups")["data"]["path"]
            with patch("creator_system.backup.PROJECT", root / "project"):
                with self.assertRaises(ControlError): backup_vault(store, root / "project/public/backups")
                with self.assertRaises(ControlError): restore_backup(archive, root / "project/src/private-vault")
            self.assertFalse((root / "project").exists())

    def test_missing_source_blob_or_evidence_prevents_verified_backup(self):
        for removed in ("blob", "evidence"):
            with self.subTest(removed=removed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                store = Store(root / "vault")
                self.addCleanup(store.close)
                source = root / "original.txt"
                source.write_text("Synthetic evidence.")
                version = register_source(store, source, "S")
                evidence = create_evidence(store, version["id"], list_units(store, version["id"])[0]["locator"])
                flow = Workflow(store)
                flow.create_project("P", "Integrity test", {"read_paths": ["."], "write_paths": ["."], "tools": [], "network": False})
                flow.register_claim("P", "C", "paraphrase", "Synthetic evidence", [{"evidence_id": evidence["id"], "relation": "supports"}])
                if removed == "blob":
                    (store.objects / version["data"]["snapshot_sha256"]).unlink()
                else:
                    store.db.execute("DELETE FROM records WHERE kind='evidence'")
                    store.db.execute("DELETE FROM revisions WHERE kind='evidence'")
                    store.db.commit()
                with self.assertRaises(ControlError): backup_vault(store, root / "backups")
                self.assertEqual(store.list("backup"), [])

    def test_current_revision_and_continuous_history_are_required(self):
        for removed_revision in (2, 3):
            with self.subTest(revision=removed_revision), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                store = Store(root / "vault")
                self.addCleanup(store.close)
                current = store.create("project", {"version": 1}, "P")
                current = store.update("project", "P", {"version": 2}, current["digest"])
                store.update("project", "P", {"version": 3}, current["digest"])
                store.db.execute("DELETE FROM revisions WHERE revision=?", (removed_revision,))
                store.db.commit()
                with self.assertRaises(ControlError): backup_vault(store, root / "backups")

    def test_archive_path_replacement_after_verify_cannot_change_restored_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            (store.vault / "note.md").write_text("Original verified note")
            backup = backup_vault(store, root / "backups")["data"]
            def swapped_after_verify(input_archive):
                result = verify_backup(input_archive)
                with zipfile.ZipFile(backup["path"]) as archive:
                    members = {name: archive.read(name) for name in archive.namelist()}
                members["vault/note.md"] = b"UNVERIFIED replacement"
                with zipfile.ZipFile(backup["path"], "w") as archive:
                    for name, value in members.items(): archive.writestr(name, value)
                return result
            with patch("creator_system.backup.verify_backup", side_effect=swapped_after_verify):
                result = restore_backup(backup["path"], root / "recovered")
            self.assertEqual((root / "recovered/note.md").read_text(), "Original verified note")
            self.assertEqual(result["archive_sha256"], backup["sha256"])

    def test_corrupted_object_is_not_blessed_by_a_new_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            key = store.blob(b"original")
            (store.objects / key).write_bytes(b"corrupt before backup")
            with self.assertRaises(ControlError):
                backup_vault(store, root / "backup")
            self.assertEqual(store.list("backup"), [])

    def test_recovery_preserves_notes_history_and_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            (store.vault / "manual.md").write_text("personal changes", encoding="utf8")
            record = store.create("project", {"goal": "one"}, "P")
            store.update("project", "P", {"goal": "two"}, record["digest"])
            fingerprint = store.blob(b"private evidence")
            backup = backup_vault(store, root / "backup")["data"]
            result = restore_backup(backup["path"], root / "recovered")
            self.assertTrue(result["verified"])
            restored = Store(root / "recovered")
            self.addCleanup(restored.close)
            self.assertEqual(restored.get("project", "P", 1)["data"]["goal"], "one")
            self.assertEqual(restored.read_blob(fingerprint), b"private evidence")
            self.assertEqual((restored.vault / "manual.md").read_text(), "personal changes")
            with self.assertRaises(ControlError):
                restore_backup(backup["path"], store.vault)

    def test_corruption_and_zip_slip_fail_before_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = Store(root / "vault")
            self.addCleanup(store.close)
            good = backup_vault(store, root / "backup")["data"]["path"]
            bad = root / "bad.zip"
            with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, "w") as dst:
                for name in src.namelist():
                    data = src.read(name)
                    if name.endswith("state.sqlite3"):
                        data = b"swapped"
                    dst.writestr(name, data)
            with self.assertRaises(ControlError):
                restore_backup(bad, root / "bad-restore")
            self.assertFalse((root / "bad-restore").exists())
            with zipfile.ZipFile(root / "slip.zip", "w") as z:
                z.writestr("manifest.json", json.dumps({"schema": 1, "files": {"../../oops": {"sha256": "x", "bytes": 1}}}))
                z.writestr("vault/../../oops", "x")
            with self.assertRaises(ControlError):
                verify_backup(root / "slip.zip")


if __name__ == "__main__":
    unittest.main()
