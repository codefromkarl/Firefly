"""Bind joined recording boundaries to scenes only when IDs and audio bytes agree."""
import json
from pathlib import Path

from .media import hash_file
from .store import ControlError
from .video import resolve_timeline


def clip_timeline(manifest, clips_file, audio_info):
    clips_file = Path(clips_file)
    clips = json.loads(clips_file.read_text())
    report = json.loads((clips_file.parent / "join-report.json").read_text())
    if report.get("status") != "joined" or report.get("hashes", {}).get("clips.json") != hash_file(clips_file):
        raise ControlError("Recording cue file does not match its join report")
    if report.get("hashes", {}).get("joined.wav") != audio_info["sha256"]:
        raise ControlError("Recording cues belong to a different audio revision")
    scenes = manifest["scenes"]
    segments = clips.get("clips", [])
    if [row.get("id") for row in scenes] != [row.get("id") for row in segments]:
        raise ControlError("Segment IDs/order must match scene IDs exactly; otherwise align the full-track timeline manually")
    timed = [{**scene, "start": clip["start"], "end": clip["end"]} for scene, clip in zip(scenes, segments)]
    result = resolve_timeline({**manifest, "scenes": timed, "timing_confirmed": False}, audio_info["duration"], preview=True)
    return {**result, "timing": "recorded_clip_boundaries", "timing_confirmed": False}
