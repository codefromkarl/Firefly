import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from creator_system.store import Store, ControlError


class StoreTests(unittest.TestCase):
    def test_interrupted_blob_commit_can_retry_without_partial_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            self.addCleanup(store.close)
            with patch("creator_system.store.os.link", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError):
                    store.blob(b"new content")
            self.assertEqual(list(store.objects.iterdir()), [])
            self.assertEqual(store.read_blob(store.blob(b"new content")), b"new content")

    def test_history_conflict_and_immutable_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            self.addCleanup(store.close)
            first = store.create("project", {"goal": "a"}, "one")
            second = store.update("project", "one", {"goal": "b"}, first["digest"])
            self.assertEqual(store.get("project", "one", 1)["data"]["goal"], "a")
            self.assertEqual(second["revision"], 2)
            with self.assertRaises(ControlError):
                store.update("project", "one", {"goal": "overwrite"}, first["digest"])
            review = store.create("review", {"result": "pending"})
            with self.assertRaises(ControlError):
                store.update("review", review["id"], {"result": "approved"}, review["digest"])

    def test_corrupt_blob_and_record_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            self.addCleanup(store.close)
            key = store.blob(b"original")
            (store.objects / key).write_bytes(b"swapped")
            with self.assertRaises(ControlError):
                store.read_blob(key)
            row = store.create("project", {"a": 1}, "one")
            store.db.execute("UPDATE records SET body='{}' WHERE id=?", (row["id"],))
            store.db.commit()
            with self.assertRaises(ControlError):
                store.get("project", "one")

    def test_symlink_state_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "vault").mkdir()
            (root / "outside").mkdir()
            (root / "vault/.creator-system").symlink_to(root / "outside", target_is_directory=True)
            with self.assertRaises(ControlError):
                Store(root / "vault")
            self.assertEqual(list((root / "outside").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
