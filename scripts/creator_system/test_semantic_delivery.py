import copy
import json
from pathlib import Path
import tempfile
import unittest

from creator_system.semantic import prepare_document, pack_fingerprint, validate_analysis, validate_review
from creator_system.semantic_delivery import compile_storyboard, export_analysis, _write_package, check_current, reports
from creator_system.store import ControlError, canonical, digest


def fixture(root):
    manuscript = root / "draft.md"
    manuscript.write_text("# Synthetic question\n\nFirst claim.\n\nSecond claim.\n")
    source = root / "source.md"
    source.write_text("---\nid: SOURCE\n---\nProvided note only.\n")
    pack = prepare_document(manuscript, [source])
    bodies = [block for block in pack["blocks"] if block["kind"] != "heading"]
    segments = []
    for index, block in enumerate(bodies):
        segments.append({"id": f"S-{index}", "title": f"Unit {index}", "role": "explanation", "claim_type": "factual",
                         "question": "What?", "thesis": block["text"], "audience_before": "Unknown", "audience_after": "Understands the stated claim",
                         "source_blocks": [block["id"]], "context_blocks": [], "reasoning_steps": ["State the claim"], "limitations": ["Synthetic fixture"],
                         "evidence": [{"source_id": "SOURCE", "relation": "background", "scope": "Provided fixture note"}], "visuals": []})
    analysis = {"schema": 1, "document_sha256": pack["document"]["sha256"], "pack_sha256": pack_fingerprint(pack), "segments": segments, "exclusions": []}
    review = {"schema": 1, "document_sha256": pack["document"]["sha256"], "analysis_sha256": digest(canonical(analysis).encode()),
              "reviewer": {"kind": "ai", "name": "fixture"}, "findings": [{"id": "F1", "segment_ids": ["S-0"], "block_ids": [bodies[0]["id"]],
              "anchors": [{"block_id": bodies[0]["id"], "quote": "First claim."}], "category": "evidence", "severity": "suggestion",
              "observation": "This is only a claim.", "reason": "The note is not primary evidence.", "impact": "More checking may be needed.",
              "options": ["Check original material."], "uncertainty": "Fixture, not a real finding.", "status": "open"}], "strengths": ["Explicit limitation"]}
    return pack, analysis, review


class SemanticDeliveryTests(unittest.TestCase):
    def test_heading_hash_in_a_word_is_not_a_closing_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text("# C#\n\n## Section ###\n\nOriginal text.\n")
            pack = prepare_document(path)
            self.assertEqual(pack["document"]["title"], "C#")
            self.assertEqual(pack["blocks"][-1]["section"], "C# / Section")

    def test_three_reports_narration_and_source_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack, analysis, review = fixture(root)
            output = root / "reports"
            first = export_analysis(pack, analysis, review, output)
            self.assertEqual(first["open_findings"], 1)
            self.assertTrue(export_analysis(pack, analysis, review, output)["reused"])
            story = json.loads((output / "storyboard.json").read_text())
            self.assertEqual([scene["narration"] for scene in story["scenes"]], ["First claim.", "Second claim."])
            self.assertEqual(story["semantic_review"]["status"], "candidate_not_author_approval")
            for name in ("论证分段稿.md", "视频分镜表.md", "反向审稿报告.md"): self.assertTrue((output / name).is_file())
            (root / "source.md").write_text("Changed source note")
            with self.assertRaises(ControlError): export_analysis(pack, analysis, review, root / "changed")

    def test_packet_forgery_and_report_cache_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack, _, _ = fixture(root)
            forged = copy.deepcopy(pack)
            forged["blocks"][1]["text"] = "Invented original words"
            with self.assertRaises(ControlError): check_current(forged)
            _write_package(root / "cache", {"report.md": "Old rule result"}, {"input": "same"})
            with self.assertRaises(ControlError): _write_package(root / "cache", {"report.md": "New rule result"}, {"input": "same"})
            self.assertEqual((root / "cache/report.md").read_text(), "Old rule result")

    def test_fallback_visual_identity_cannot_collide_with_explicit_visual(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack, analysis, _ = fixture(Path(tmp))
            segment = analysis["segments"][1]
            segment["visuals"] = [{"id": "S-0-text", "type": "text", "purpose": "Show second", "text": "Second claim.", "source_blocks": segment["source_blocks"]}]
            story = compile_storyboard(pack, analysis)
            ids = [scene["id"] for scene in story["scenes"]]
            self.assertEqual(len(ids), len(set(ids)))
            rendered = reports(pack, analysis, storyboard_plan=story)["视频分镜表.md"]
            self.assertTrue(all(identity in rendered for identity in ids))

    def test_field_types_and_empty_review_target_do_not_silently_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack, analysis, review = fixture(Path(tmp))
            invalid = copy.deepcopy(analysis)
            invalid["segments"][0]["reasoning_steps"] = [{"premise": "A", "conclusion": "B"}]
            self.assertFalse(validate_analysis(pack, invalid)["valid"])
            review["findings"][0]["segment_ids"] = []
            self.assertFalse(validate_review(pack, analysis, review)["valid"])

    def test_duplicate_narration_allocation_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack, analysis, _ = fixture(Path(tmp))
            segment = analysis["segments"][0]
            segment["visuals"] = [{"id": f"V{i}", "type": "text", "purpose": "Fixture", "text": "Summary", "source_blocks": segment["source_blocks"], "narration_blocks": segment["source_blocks"]} for i in range(2)]
            with self.assertRaises(ControlError): compile_storyboard(pack, analysis)
