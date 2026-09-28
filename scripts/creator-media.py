#!/usr/bin/env python3
"""Build article delivery packages and still-image videos using your own recording."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from creator_system.media import plan_document, render_frames, hash_file
from creator_system.video import assemble_video, probe_audio, resolve_timeline
from creator_system.store import ControlError, Store, canonical, digest, safe_path

PROJECT = Path(__file__).resolve().parent.parent


def private_path(value):
    path = Path(os.path.abspath(Path(value).expanduser()))
    for candidate in [path, *path.parents]:
        if candidate.is_symlink(): raise ControlError("Delivery output must not traverse symlinks")
    if path.is_relative_to(PROJECT) and not path.is_relative_to(PROJECT / ".local"):
        raise ControlError("Project-local delivery output must stay under .local")
    return path


def write_new(path, value):
    path = private_path(path)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        if path.read_text() != content: raise ControlError("Existing plan/output differs; keep edits and use a new file")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as stream: stream.write(content)


def bilibili(article, output, assets=None):
    command = ["node", str(PROJECT / "scripts/creator_system/bilibili-render.mjs"), "--input", str(article), "--output", str(private_path(output))]
    if assets: command += ["--assets", str(assets)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode: raise ControlError(result.stderr[-1600:] or "Article export failed")
    return json.loads(result.stdout)


def build(article, output, visuals=None, audio=None, store=None):
    output = private_path(output)
    plan = plan_document(article, visuals)
    if audio: plan["audio"] = {"path": str(Path(audio).expanduser().resolve())}
    marker = output / ".delivery-build.json"
    identity = {"document": hash_file(article), "visuals": hash_file(visuals) if visuals else None,
                "audio": hash_file(audio) if audio else None, "builder": hash_file(__file__)}
    if plan["document_sha256"] != identity["document"]:
        raise ControlError("Document changed while planning; retry a stable revision")
    signature = digest(canonical(identity).encode())
    if output.exists():
        previous = json.loads(marker.read_text()) if marker.is_file() else {}
        if previous.get("signature") != signature or digest(canonical(previous.get("inputs", {})).encode()) != signature:
            raise ControlError("Delivery directory already exists for other inputs; choose a new version directory")
        for name, fingerprint in previous.get("files", {}).items():
            if hash_file(safe_path(output, name)) != fingerprint: raise ControlError("A build-owned file was edited; preserve it and use a new output version")
    else:
        output.mkdir(parents=True)
        write_new(marker, {"signature": signature, "inputs": identity, "status": "building"})
    storyboard = output / "storyboard.json"
    write_new(storyboard, plan)
    frames = render_frames(storyboard, output / "frames", store=store)
    layout = json.loads((output / "frames/layout-report.json").read_text())
    by_id = {scene["id"]: scene for scene in plan["scenes"]}
    images = []
    for scene in layout:
        if scene["type"] not in {"quote", "book", "map"}: continue
        row = {"id": scene["id"], "path": "frames/" + scene["image"], "caption": scene["caption"],
               "source": "local_catalog" if scene["type"] in {"quote", "book"} else "provided"}
        if by_id[scene["id"]].get("article_after_heading"): row["after_heading"] = by_id[scene["id"]]["article_after_heading"]
        images.append(row)
    headings = list(dict.fromkeys(scene["heading"] for scene in plan["scenes"] if scene["type"] == "text"))
    images.sort(key=lambda row: headings.index(row["after_heading"]) if row.get("after_heading") in headings else len(headings))
    assets = output / "article-assets.json"
    write_new(assets, {"schema": 1, "images": images})
    article_result = bilibili(article, output / "bilibili", assets)
    video = assemble_video(output / "frames/frames.json", output / "video-preview", preview=True)
    article_marker = json.loads((output / "bilibili/.creator-bilibili.json").read_text())
    if article_marker.get("inputs", {}).get("article") != identity["document"]:
        raise ControlError("Article and storyboard captured different document revisions")
    if hash_file(article) != identity["document"] or (visuals and hash_file(visuals) != identity["visuals"]):
        raise ControlError("Source inputs changed during delivery build; keep the partial output and use a stable new revision")
    if audio and (hash_file(audio) != identity["audio"] or video.get("audio", {}).get("sha256") != identity["audio"]):
        raise ControlError("Audio revision differs between planning and assembly")
    report_path = output / "delivery-report.json"
    if report_path.exists():
        return {**json.loads(report_path.read_text()), "reused": True}
    result = {"status": "local_delivery_ready" if audio else "article_and_frames_ready_recording_required",
              "storyboard": str(storyboard), "frames": frames, "article": article_result, "video": video,
              "platform_verified": False, "published": False,
              "next_step": "Review estimated timings against your recording, then create an explicit confirmed timeline." if audio else "Supply the path to your own recording; no substitute narration was generated."}
    write_new(report_path, result)
    owned = {name: hash_file(output / name) for name in ("storyboard.json", "article-assets.json", "delivery-report.json")}
    marker.write_text(json.dumps({"signature": signature, "inputs": identity, "files": owned, "status": "complete"}, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, help="Optional existing vault for evidence-backed quote frames")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "build"):
        command = commands.add_parser(name)
        command.add_argument("--input", required=True, type=Path)
        command.add_argument("--output", required=True, type=Path)
        command.add_argument("--visuals", type=Path)
        if name == "build": command.add_argument("--audio", type=Path)
    frames = commands.add_parser("frames")
    frames.add_argument("--plan", required=True, type=Path)
    frames.add_argument("--output", required=True, type=Path)
    frames.add_argument("--audio", type=Path)
    for name in ("video", "timeline"):
        command = commands.add_parser(name)
        command.add_argument("--frames", required=True, type=Path)
        command.add_argument("--output", required=True, type=Path)
        if name == "video": command.add_argument("--preview", action="store_true")
        if name == "timeline": command.add_argument("--clip-cues", type=Path, help="Optional clips.json from audio-join; scene IDs must match")
    audio = commands.add_parser("audio-info")
    audio.add_argument("--audio", required=True, type=Path)
    join = commands.add_parser("audio-join", help="Join your ordered recording clips without trimming or changing speed")
    join.add_argument("--clips", required=True, type=Path)
    join.add_argument("--output", required=True, type=Path)
    prepare = commands.add_parser("semantic-prepare", help="Create exact manuscript/source packet and AI handoff tasks")
    prepare.add_argument("--input", required=True, type=Path)
    prepare.add_argument("--sources-dir", type=Path)
    prepare.add_argument("--output", required=True, type=Path)
    for name in ("semantic-check", "semantic-export"):
        command = commands.add_parser(name)
        command.add_argument("--packet", required=True, type=Path)
        command.add_argument("--analysis", required=True, type=Path)
        command.add_argument("--review", type=Path)
        if name == "semantic-export": command.add_argument("--output", required=True, type=Path)
    compare = commands.add_parser("semantic-compare", help="Compare revised manuscript against bound analysis and identify affected scenes/recording")
    compare.add_argument("--before", required=True, type=Path)
    compare.add_argument("--input", required=True, type=Path)
    compare.add_argument("--analysis", required=True, type=Path)
    compare.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    store = None
    try:
        if args.vault:
            if not (args.vault / ".creator-system/state.sqlite3").is_file(): raise ControlError("Evidence rendering requires an existing initialized vault")
            store = Store(args.vault)
        if args.command == "semantic-prepare":
            from creator_system.semantic_delivery import prepare_handoff
            source_paths = sorted(args.sources_dir.glob("SRC-*.md")) if args.sources_dir else []
            result = prepare_handoff(args.input, source_paths, args.output)
        elif args.command in {"semantic-check", "semantic-export"}:
            from creator_system.semantic import validate_analysis, validate_review
            from creator_system.semantic_delivery import check_current, export_analysis
            pack = json.loads(args.packet.read_text())
            analysis = json.loads(args.analysis.read_text())
            review = json.loads(args.review.read_text()) if args.review else None
            check_current(pack)
            if args.command == "semantic-export":
                result = export_analysis(pack, analysis, review, args.output)
            else:
                results = {"analysis": validate_analysis(pack, analysis), "review": validate_review(pack, analysis, review) if review is not None else None}
                result = {**results, "valid": all(item is None or item["valid"] for item in results.values()), "author_approved": False}
        elif args.command == "semantic-compare":
            from creator_system.semantic import prepare_document, compare_documents
            pack = json.loads(args.before.read_text())
            analysis = json.loads(args.analysis.read_text())
            revised = prepare_document(args.input, [source["path"] for source in pack.get("sources", [])])
            result = compare_documents(pack, revised, analysis)
            write_new(args.output, result)
        elif args.command == "plan":
            plan = plan_document(args.input, args.visuals)
            write_new(args.output, plan)
            result = {"path": str(args.output), "scenes": len(plan["scenes"]), "timing_confirmed": False}
        elif args.command == "frames": result = render_frames(args.plan, args.output, audio_path=args.audio, store=store)
        elif args.command == "video": result = assemble_video(args.frames, args.output, preview=args.preview)
        elif args.command == "audio-info": result = probe_audio(args.audio)
        elif args.command == "audio-join":
            from creator_system.audio_join import join_recordings
            result = join_recordings(args.clips, args.output)
        elif args.command == "timeline":
            manifest = json.loads(args.frames.read_text())
            path = (manifest.get("audio") or {}).get("path")
            if not path: raise ControlError("Add your recording to frames.json before estimating cues")
            info = probe_audio(args.frames.parent / path)
            if args.clip_cues:
                from creator_system.media_timing import clip_timeline
                resolved = clip_timeline(manifest, args.clip_cues, info)
            else:
                resolved = resolve_timeline(manifest, info["duration"], preview=True)
            # A copied timeline lives in a different folder; preserve image and audio references.
            images = [{**scene, "image": str((args.frames.parent / scene["image"]).resolve())} for scene in resolved["scenes"]]
            prepared = {**manifest, "audio": {"path": str((args.frames.parent / path).resolve()), "sha256": info["sha256"]},
                        "timing_confirmed": False, "scenes": images}
            write_new(args.output, prepared)
            result = {"path": str(args.output), "timing": resolved["timing"], "timing_confirmed": False, "action": "Listen to the recording, adjust start/end and explicitly confirm timings."}
        else: result = build(args.input, args.output, args.visuals, args.audio, store)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "semantic-check" and not result["valid"]: sys.exit(2)
    finally:
        if store: store.close()


if __name__ == "__main__":
    try: main()
    except (ControlError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"error": str(error), "completed": False}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
