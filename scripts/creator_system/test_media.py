from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw
from creator_system.media import plan_document, render_frames, render_scene, resolve_scene, public_text, wrap, font
from creator_system.store import ControlError


class MediaTests(unittest.TestCase):
    def test_chinese_punctuation_does_not_start_a_line(self):
        draw = ImageDraw.Draw(Image.new("RGB", (600, 300)))
        lines = wrap(draw, "财富自由是什么？请先说清自己的问题。", font(40), 240)
        self.assertFalse(any(line and line[0] in "，。！？；：”" for line in lines))
        self.assertEqual("".join(lines), "财富自由是什么？请先说清自己的问题。")

    def test_plan_keeps_existing_text_and_labels_outline_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "article.md"
            path.write_text("---\nprivate: /home/user/secret\n---\n# 测试问题\n\n## 第一个步骤\n\n这是已有的正文。\n\n## 第二个步骤\n\n这是另一个段落。\n")
            plan = plan_document(path)
            self.assertEqual(plan["title"], "测试问题")
            self.assertFalse(plan["timing_confirmed"])
            maps = [scene for scene in plan["scenes"] if scene["type"] == "map"]
            self.assertEqual(maps[0]["diagram_basis"], "document_outline")
            self.assertEqual([node["label"] for node in maps[0]["nodes"]][1:], ["第一个步骤", "第二个步骤"])
            self.assertEqual([scene["text"] for scene in plan["scenes"] if scene["type"] == "text"], ["这是已有的正文。", "这是另一个段落。"])

    def test_cover_and_quote_are_bound_to_exact_catalogue_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            book = root / "src/content/books/test-book"
            book.mkdir(parents=True)
            (book / "index.md").write_text('---\ntitle: 测试书籍\nauthors: [作者]\ncover: ./cover.png\nexcerpts:\n  - text: 必须保持原句。\n    source: 第一节\n---\n')
            Image.new("RGB", (200, 300), "navy").save(book / "cover.png")
            with patch("creator_system.media.PROJECT", root):
                scene, cover, _ = resolve_scene({"type": "quote", "book_id": "test-book", "excerpt_index": 0})
                self.assertEqual(scene["text"], "必须保持原句。")
                image, _ = render_scene(scene, cover)
                self.assertEqual(image.size, (1920, 1080))
                with self.assertRaises(ControlError):
                    resolve_scene({"type": "quote", "book_id": "test-book", "excerpt_index": 0, "text": "伪造的文字"})
                with self.assertRaises(ControlError):
                    resolve_scene({"type": "quote", "book_id": "test-book", "text": "没有来源的文字"})

    def test_overflow_bad_graph_and_private_text_fail_without_truncation(self):
        with self.assertRaises(ControlError):
            render_scene({"type": "text", "heading": "过长", "text": "内容" * 2000})
        with self.assertRaises(ControlError):
            render_scene({"type": "map", "heading": "错误图", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], "edges": [{"from": "a", "to": "missing"}]})
        for text in ["/home/person/private", "D:/private/file", r"\\NAS\private\file", "[[内部笔记]]"]:
            with self.assertRaises(ControlError): public_text(text)

    def test_render_cache_preserves_user_edits_and_requires_recording(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            plan.write_text(json.dumps({"schema": 1, "title": "测试", "scenes": [{"id": "one", "type": "title", "heading": "测试"}]}))
            first = render_frames(plan, root / "frames")
            self.assertEqual(first["status"], "frames_ready_recording_required")
            self.assertTrue(render_frames(plan, root / "frames")["reused"])
            (root / "frames/frame-001.png").write_bytes(b"user change")
            with self.assertRaises(ControlError): render_frames(plan, root / "frames")
            self.assertEqual((root / "frames/frame-001.png").read_bytes(), b"user change")

    def test_cli_build_produces_article_and_maps_without_fabricating_audio(self):
        cli = Path(__file__).resolve().parents[1] / "creator-media.py"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            article.write_text("# 流程测试\n\n## 资料输入\n\n保留已有正文。\n")
            argv = [sys.executable, "-B", str(cli), "build", "--input", str(article), "--output", str(root / "delivery")]
            first = subprocess.run(argv, capture_output=True, text=True, timeout=90)
            self.assertEqual(first.returncode, 0, first.stderr)
            result = json.loads(first.stdout)
            self.assertEqual(result["video"]["status"], "missing_audio")
            self.assertTrue((root / "delivery/bilibili/bilibili.html").is_file())
            self.assertFalse((root / "delivery/video-preview/video.mp4").exists())
            again = subprocess.run(argv, capture_output=True, text=True, timeout=90)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertTrue(json.loads(again.stdout)["reused"])
