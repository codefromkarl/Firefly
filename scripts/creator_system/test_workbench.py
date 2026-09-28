from pathlib import Path
import tempfile
import unittest
from creator_system.store import Store, digest
from creator_system.workbench import track_legacy_notes, propose_change, candidate_status


class WorkbenchTests(unittest.TestCase):
    def test_legacy_rename_keeps_identity_without_promoting_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            self.addCleanup(store.close)
            folder = Path(tmp) / "50 来源"
            folder.mkdir()
            note = folder / "original.md"
            raw = "---\ntype: source\nid: S1\nverification: text_checked\n---\nMy note\n"
            note.write_text(raw)
            track_legacy_notes(store)
            first = store.list("legacy_note")[0]
            note.rename(folder / "renamed.md")
            track_legacy_notes(store)
            current = store.list("legacy_note")
            self.assertEqual(len(current), 1)
            self.assertEqual(current[0]["id"], first["id"])
            self.assertEqual(current[0]["data"]["effective_review"], "legacy_unverified")
            self.assertEqual((folder / "renamed.md").read_text(), raw)

    def test_candidate_preserves_intervening_user_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            self.addCleanup(store.close)
            note = Path(tmp) / "draft.md"
            note.write_text("first")
            base = digest(note.read_bytes())
            note.write_text("user update")
            candidate = propose_change(store, "draft.md", "AI candidate", base)
            self.assertEqual(candidate_status(store, candidate["candidate_id"])["status"], "conflict")
            self.assertEqual(note.read_text(), "user update")


if __name__ == "__main__":
    unittest.main()
