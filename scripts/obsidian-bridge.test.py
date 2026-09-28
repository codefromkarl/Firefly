"""Run with python3 scripts/obsidian-bridge.test.py (stdlib unittest + PyYAML)."""
import importlib.util
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('bridge', Path(__file__).with_name('obsidian-bridge.py'))
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTest(unittest.TestCase):
    def test_plan_idempotence_and_user_edit_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / 'vault'
            files = {'10 书籍/book.md': '# Existing\n'}
            bridge.apply_files(vault, files)
            self.assertFalse(vault.exists())
            bridge.apply_files(vault, files, True)
            plan, conflicts = bridge.apply_files(vault, files, True)
            self.assertEqual(plan[0]['action'], 'unchanged')
            self.assertFalse(conflicts)
            (vault / '10 书籍/book.md').write_text('MY NOTES')
            _, conflicts = bridge.apply_files(vault, {**files, 'new.md': 'new'}, True)
            self.assertTrue(conflicts)
            self.assertEqual((vault / '10 书籍/book.md').read_text(), 'MY NOTES')
            self.assertFalse((vault / 'new.md').exists())

    def test_obsidian_base_reserialization_is_not_a_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'books.base').write_text('views:\n  - type: table\n    name: Books\n')
            plan, conflicts = bridge.apply_files(root, {'books.base': 'views:\n- type: table\n  name: Books\n'}, True)
            self.assertFalse(conflicts)
            self.assertEqual(plan[0]['action'], 'unchanged')
            self.assertIn('  - type', (root / 'books.base').read_text())

    def test_symlink_target_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'vault').mkdir()
            (root / 'outside').mkdir()
            (root / 'vault/10 书籍').symlink_to(root / 'outside', target_is_directory=True)
            with self.assertRaises(ValueError):
                bridge.apply_files(root / 'vault', {'10 书籍/book.md': 'bad'}, True)
            self.assertEqual(list((root / 'outside').iterdir()), [])

    def test_metadata_preserves_preview_and_original_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'book').mkdir()
            (root / 'book/index.md').write_text('---\ntitle: Example\nauthors: [Author]\nstatus: wishlist\ngraphStage: preview\nintroductions:\n  - source: Publisher\n    url: https://example.org\n---\nAI 预读，尚未读完。')
            content = bridge.book_notes(root)['10 书籍/book.md']
            self.assertIn('reading_status: wishlist', content)
            self.assertIn('graph_stage: preview', content)
            self.assertIn('https://example.org', content)
            self.assertIn('AI 预读，尚未读完。', content)

    def test_bad_epub_does_not_hide_other_files_or_guess_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bad.epub').write_bytes(b'invalid')
            (root / 'one.pdf').write_bytes(b'%PDF-test')
            (root / 'copy.pdf').write_bytes(b'%PDF-test')
            (root / 'not-a-book.json').write_text('{}')
            report = bridge.inventory([root])
            self.assertEqual(len(report['files']), 3)
            self.assertEqual(len(report['byte_identical_groups']), 1)
            self.assertEqual(sum(x['validation'] == 'invalid_or_unreadable' for x in report['files']), 1)
            self.assertTrue(all(x['reading_status'] == 'unknown' for x in report['files']))
            self.assertIn('scan_started_at', report)

    def test_valid_epub_metadata_without_importing_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / 'valid.epub', 'w') as z:
                z.writestr('mimetype', 'application/epub+zip')
                z.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="book.opf"/></rootfiles></container>')
                z.writestr('book.opf', '<package xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Title</dc:title><dc:creator>Author</dc:creator></metadata></package>')
                z.writestr('body.xhtml', 'private entire book')
            row = bridge.inventory([root])['files'][0]
            self.assertEqual(row['title'], ['Title'])
            self.assertEqual(row['validation'], 'zip_crc_container_opf_pass')
            self.assertNotIn('private entire book', str(row))


if __name__ == '__main__':
    unittest.main()
