import json
from pathlib import Path
import tempfile
import unittest
from creator_system.media import hash_file
from creator_system.media_timing import clip_timeline
from creator_system.store import ControlError


class MediaTimingTests(unittest.TestCase):
    def test_clip_positions_require_matching_audio_and_scene_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "clips.json"
            path.write_text(json.dumps({"clips": [{"id": "one", "start": 0, "end": 1}, {"id": "two", "start": 1, "end": 3}]}))
            (root / "join-report.json").write_text(json.dumps({"status": "joined", "hashes": {"clips.json": hash_file(path), "joined.wav": "audio-identity"}}))
            manifest = {"scenes": [{"id": "one"}, {"id": "two"}]}
            audio = {"duration": 3, "sha256": "audio-identity"}
            result = clip_timeline(manifest, path, audio)
            self.assertEqual(result["timing"], "recorded_clip_boundaries")
            self.assertFalse(result["timing_confirmed"])
            self.assertEqual(result["scenes"][1]["start"], 1)
            with self.assertRaises(ControlError): clip_timeline(manifest, path, {**audio, "sha256": "different"})
            with self.assertRaises(ControlError): clip_timeline({"scenes": list(reversed(manifest["scenes"]))}, path, audio)
