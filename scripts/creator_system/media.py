"""Deterministic document-to-storyboard and book/quote/map frame rendering."""
import html
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import tempfile

import yaml
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .store import ControlError, canonical, digest, safe_path

PROJECT = Path(__file__).resolve().parents[2]
WIDTH, HEIGHT = 1920, 1080
PALETTE = {"paper": "#F7F9FC", "ink": "#16324F", "blue": "#295CCB", "green": "#2F7768", "line": "#D8E0EC", "white": "#FFFFFF"}
FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")


def public_text(value):
    if not isinstance(value, str): raise ControlError("Visual text must be a string")
    if re.search(r"\[\[|%%|(?:file|obsidian)://|/home/|/Users/|(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\", value):
        raise ControlError("Visual text contains an internal link or private path")
    return value


def clean_markdown(text):
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if text.startswith("---\n"):
        match = re.match(r"---\n.*?\n---(?:\n|$)", text, re.S)
        if not match: raise ControlError("Unclosed document frontmatter")
        text = text[match.end():]
    public_text(text)
    if re.search(r"!\[|```|<[/!A-Za-z][^>]*>", text):
        raise ControlError("Storyboard input currently accepts prose Markdown; use explicit visuals for images/code/HTML")
    return text.strip()


def prose(text):
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", text)
    text = re.sub(r"(?m)^\s*(?:>\s*|[-*+]\s+|\d+[.)]\s+)", "", text)
    return text.replace("**", "").replace("__", "").replace("`", "").strip()


def chunks(text, limit=180):
    text = prose(text)
    while len(text) > limit:
        boundary = max(text.rfind(mark, 0, limit + 1) for mark in "。！？；\n")
        end = boundary + 1 if boundary > limit // 3 else limit
        yield text[:end].strip()
        text = text[end:].strip()
    if text: yield text


def plan_document(input_path, visuals_path=None):
    if Path(input_path).stat().st_size > 2 * 1024**2: raise ControlError("Document exceeds the local storyboard input limit")
    raw = Path(input_path).read_bytes()
    text = clean_markdown(raw.decode("utf8"))
    title_match = re.search(r"(?m)^# ([^\n]+)", text)
    title = prose(title_match[1]) if title_match else Path(input_path).stem
    title = public_text(title)
    sections = []
    current = {"heading": title, "blocks": []}
    for block in re.split(r"\n\s*\n", text):
        heading = re.fullmatch(r"(#{1,6})\s+([^\n]+)", block.strip())
        if heading:
            if current["blocks"]: sections.append(current)
            current = {"heading": prose(heading[2]), "blocks": []}
        elif block.strip() not in {"---", "***", "___"}:
            current["blocks"].append(block)
    if current["blocks"]: sections.append(current)
    scenes = [{"type": "title", "heading": title, "text": "", "narration": title, "source_refs": []}]
    headings = list(dict.fromkeys(section["heading"] for section in sections if section["heading"] != title))
    for offset in range(0, len(headings), 4):
        subset = headings[offset:offset + 4]
        nodes = [{"id": "root", "label": title}] + [{"id": f"h{i}", "label": heading} for i, heading in enumerate(subset)]
        scenes.append({"type": "map", "heading": "问题主线" if len(headings) <= 4 else f"问题主线 · {offset // 4 + 1}",
                       "nodes": nodes, "edges": [{"from": "root", "to": f"h{i}", "label": ""} for i in range(len(subset))],
                       "diagram_basis": "document_outline", "narration": "。".join(subset), "source_refs": []})
    for section in sections:
        for block in section["blocks"]:
            for part in chunks(block):
                scenes.append({"type": "text", "heading": section["heading"], "text": part, "narration": part, "source_refs": []})
    if visuals_path:
        extra = json.loads(Path(visuals_path).read_text())
        if extra.get("schema") != 1 or not isinstance(extra.get("scenes"), list): raise ControlError("Expected visual schema 1 and scenes list")
        for visual in extra["scenes"]:
            if visual.get("type") not in {"quote", "map", "book", "text"}: raise ControlError("Unsupported explicit visual")
            visual = dict(visual)
            after = visual.pop("after_heading", None)
            if after: visual["article_after_heading"] = after
            if after is None:
                scenes.append(visual)
            else:
                positions = [i for i, scene in enumerate(scenes) if scene.get("heading") == after and scene["type"] == "text"]
                if not positions: raise ControlError(f"No section matches visual placement: {after}")
                scenes.insert(positions[-1] + 1, visual)
    for index, scene in enumerate(scenes, 1): scene.setdefault("id", f"scene-{index:03d}")
    return {"schema": 1, "title": title, "width": WIDTH, "height": HEIGHT, "fps": 30,
            "document_sha256": digest(raw), "planning_basis": "existing_document_and_explicit_visuals",
            "timing_confirmed": False, "audio": None, "demo_audio": False, "scenes": scenes}


def font(size, bold=False):
    path = BOLD if bold else FONT
    if not path.is_file(): raise ControlError(f"Chinese font missing: {path.name}")
    return ImageFont.truetype(str(path), size, index=2)


def hash_file(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): value.update(chunk)
    return value.hexdigest()


def wrap(draw, text, face, width):
    lines = []
    forbidden_start = set("，。！？；：、）》」』】〕〉”’…%!?;:,.%)]}")
    forbidden_end = set("（《「『【〔〈“‘([{")
    for paragraph in public_text(text).split("\n"):
        line = ""
        for character in paragraph:
            if line and draw.textlength(line + character, font=face) > width:
                moved = ""
                if character in forbidden_start:
                    split = len(line) - 1
                    while split > 0 and line[split] in forbidden_start: split -= 1
                    moved, line = line[split:], line[:split]
                while line and line[-1] in forbidden_end:
                    moved, line = line[-1] + moved, line[:-1]
                if line: lines.append(line)
                line = moved + character
            else: line += character
        lines.append(line)
    return lines


def text_box(draw, text, box, *, size=56, minimum=38, color=None, bold=False, align="left", balanced=False, vertical="top"):
    x, y, width, height = box
    for point in range(size, minimum - 1, -2):
        face = font(point, bold)
        lines = wrap(draw, text, face, width)
        if balanced and "\n" not in text and 2 <= len(lines) <= 4:
            desired = min(width, math.ceil(draw.textlength(text, font=face) / len(lines) * 1.08))
            for candidate_width in range(desired, int(width) + 1, 8):
                balanced_lines = wrap(draw, text, face, candidate_width)
                if len(balanced_lines) <= len(lines):
                    lines = balanced_lines
                    break
        leading = round(point * 1.46)
        if len(lines) * leading <= height and all(draw.textlength(line, font=face) <= width for line in lines):
            top = y + (height - len(lines) * leading) / 2 if vertical == "center" else y
            for index, line in enumerate(lines):
                dx = x + (width - draw.textlength(line, font=face)) / 2 if align == "center" else x
                draw.text((dx, top + index * leading), line, font=face, fill=color or PALETTE["ink"], anchor="lt")
            return {"font_size": point, "lines": len(lines), "box": list(box), "text": text}
    raise ControlError("Visual text does not fit at readable size; split this scene or shorten its display text")


def catalogue_book(book_id):
    if not isinstance(book_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", book_id): raise ControlError("Invalid book id")
    directory = PROJECT / "src/content/books" / book_id
    raw = (directory / "index.md").read_bytes()
    match = re.match(r"---\r?\n(.*?)\r?\n---", raw.decode(), re.S)
    if not match: raise ControlError("Book metadata is unavailable")
    data = yaml.safe_load(match[1])
    cover = data.get("cover", "./cover.webp")
    if not isinstance(cover, str): raise ControlError("Book cover must be an explicit local asset")
    cover_path = safe_path(directory, cover)
    if not cover_path.is_file(): raise ControlError("Book cover file is missing")
    cover_bytes = cover_path.read_bytes()
    if len(cover_bytes) > 20 * 1024**2: raise ControlError("Cover exceeds local processing limit")
    return data, cover_bytes, {"book_id": book_id, "catalogue_sha256": digest(raw), "cover_sha256": digest(cover_bytes)}


def resolve_scene(scene, *, store=None):
    result = dict(scene)
    assets = []
    cover = None
    if result.get("type") in {"quote", "book"}:
        data, cover, fingerprint = catalogue_book(result.get("book_id"))
        assets.append(fingerprint)
        result["book_title"] = public_text(data["title"])
        result["authors"] = "、".join(data.get("authors", []))
        if result["type"] == "quote":
            if "excerpt_index" in result:
                index = result["excerpt_index"]
                excerpts = data.get("excerpts", [])
                if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(excerpts): raise ControlError("Book excerpt index is unavailable")
                if result.get("text") and result["text"] != excerpts[index]["text"]: raise ControlError("Quote text differs from selected catalogue excerpt")
                result["text"] = excerpts[index]["text"]
                result["source_label"] = f"《{data['title']}》 · {excerpts[index]['source']}"
                result["quote_basis"] = "catalogue_excerpt_record"
                result["source_refs"] = [{"book_id": result["book_id"], "excerpt_index": index, "locator": excerpts[index]["source"], **fingerprint}]
            elif result.get("evidence_id"):
                if store is None: raise ControlError("Evidence quote needs --vault with the existing evidence store")
                from .sources import replay_evidence
                evidence = replay_evidence(store, result["evidence_id"])
                version = store.get("source_version", evidence["source_version_id"])
                source = store.get("source", version["data"]["source_id"])
                if source["data"].get("work_id") != result["book_id"]: raise ControlError("Evidence work identity does not match the displayed book cover")
                if result.get("text") and result["text"] != evidence["quote"]: raise ControlError("Quote differs from evidence")
                if any(evidence["source_status"].get(key) for key in ("withdrawn", "active_version_changed", "current_source_changed", "current_source_unavailable")):
                    raise ControlError("Evidence is stale; review the source before rendering the quote")
                result["text"] = evidence["quote"]
                result["source_label"] = result.get("source_label") or f"《{data['title']}》 · 原文摘录"
                result["quote_basis"] = "literal_evidence_replay"
                result["source_refs"] = [{"evidence_id": evidence["evidence_id"], "source_version_id": evidence["source_version_id"], "locator": evidence["locator"]}]
            else: raise ControlError("Quote scenes require catalogue excerpt_index or evidence_id; arbitrary text is not a verified quotation")
            if len(result["text"]) > 240: raise ControlError("Quote card exceeds the 240-character excerpt bound")
        else:
            result.setdefault("text", "")
            result.setdefault("source_label", f"《{data['title']}》 · {result['authors']}")
        result.setdefault("heading", result["book_title"])
    result.setdefault("heading", "")
    result.setdefault("source_label", "")
    result.setdefault("narration", result.get("text", result["heading"]))
    for field in ("heading", "text", "source_label", "narration"):
        if field in result: public_text(result[field])
    result.setdefault("source_refs", [])
    return result, cover, assets


def arrow(draw, start, end, *, color):
    draw.line([start, end], fill=color, width=5)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    a = (end[0] - 18 * math.cos(angle - .45), end[1] - 18 * math.sin(angle - .45))
    b = (end[0] - 18 * math.cos(angle + .45), end[1] - 18 * math.sin(angle + .45))
    draw.polygon([end, a, b], fill=color)


def render_scene(scene, cover=None):
    image = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["paper"])
    draw = ImageDraw.Draw(image)
    layouts = []
    kind = scene["type"]
    if kind == "title":
        draw.rectangle((0, 0, 26, HEIGHT), fill=PALETTE["blue"])
        layouts.append(text_box(draw, scene["heading"], (116, 280, 1660, 420), size=102, minimum=64, bold=True))
        if scene.get("text"): layouts.append(text_box(draw, scene["text"], (120, 760, 1550, 150), size=44))
    else:
        layouts.append(text_box(draw, scene["heading"], (96, 75, 1728, 155), size=68, minimum=46, bold=True))
        draw.line((96, 225, 1824, 225), fill=PALETTE["line"], width=3)
        if kind in {"book", "quote"}:
            if cover is None: raise ControlError("Book frame requires a real cover")
            with Image.open(io.BytesIO(cover)) as source:
                if source.width * source.height > 40_000_000: raise ControlError("Cover dimensions too large")
                thumbnail = ImageOps.contain(ImageOps.exif_transpose(source).convert("RGB"), (380, 570))
                image.paste(thumbnail, (100 + (380 - thumbnail.width) // 2, 295 + (570 - thumbnail.height) // 2))
            draw.line((540, 290, 540, 870), fill=PALETTE["line"], width=3)
            text = f"“{scene['text']}”" if kind == "quote" else scene.get("text", "")
            layouts.append(text_box(draw, text, (610, 310, 1160, 550), size=66, minimum=40, balanced=True, vertical="center"))
            layouts.append(text_box(draw, scene["source_label"], (610, 885, 1160, 115), size=32, minimum=26, color=PALETTE["green"]))
        elif kind == "text":
            layouts.append(text_box(draw, scene.get("text", ""), (115, 305, 1690, 600), size=64, minimum=42))
            if scene.get("source_label"):
                layouts.append(text_box(draw, scene["source_label"], (96, 990, 1728, 55), size=28, minimum=24, color=PALETTE["green"]))
        elif kind == "map":
            nodes, edges = scene.get("nodes", []), scene.get("edges", [])
            if not 2 <= len(nodes) <= 5: raise ControlError("Readable map frames need 2–5 nodes; split larger maps into a series")
            identities = [node.get("id") for node in nodes]
            if len(set(identities)) != len(nodes) or any(not isinstance(value, str) or not value for value in identities): raise ControlError("Map node IDs must be unique strings")
            positions = {identities[0]: (110, 480, 460, 225)}
            count = len(nodes) - 1
            gap = 160
            top = 590 - (count * gap - 30) / 2
            for index, node in enumerate(nodes[1:]): positions[node["id"]] = (855, top + index * gap, 930, 130)
            for edge in edges:
                if edge.get("from") not in positions or edge.get("to") not in positions or edge["from"] == edge["to"]: raise ControlError("Map edge has unknown or identical endpoints")
                sx, sy, sw, sh = positions[edge["from"]]
                tx, ty, tw, th = positions[edge["to"]]
                if sx == tx:
                    start, end = ((sx + sw - 50, sy + sh), (tx + tw - 50, ty)) if ty > sy else ((sx + sw - 50, sy), (tx + tw - 50, ty + th))
                elif sx > tx:
                    start, end = (sx, sy + sh / 2), (tx + tw, ty + th / 2)
                else:
                    start, end = (sx + sw, sy + sh / 2), (tx, ty + th / 2)
                arrow(draw, start, end, color=PALETTE["line"])
                if edge.get("label"):
                    layouts.append(text_box(draw, edge["label"], ((start[0] + end[0]) / 2 - 100, (start[1] + end[1]) / 2 - 42, 200, 70), size=28, minimum=24, align="center"))
            for index, node in enumerate(nodes):
                box = positions[node["id"]]
                x, y, w, h = box
                draw.rounded_rectangle((x, y, x + w, y + h), radius=18, fill=PALETTE["blue"] if index == 0 else PALETTE["white"], outline=PALETTE["line"], width=2)
                layouts.append(text_box(draw, public_text(node["label"]), (x + 28, y + 23, w - 56, h - 40), size=48, minimum=32,
                                        color=PALETTE["white"] if index == 0 else PALETTE["ink"], bold=index == 0, align="center", balanced=True, vertical="center"))
            label = "文稿结构导图" if scene.get("diagram_basis") == "document_outline" else "知识关系图"
            if scene.get("source_label"): label += " · " + scene["source_label"]
            layouts.append(text_box(draw, label, (96, 990, 1200, 55), size=28, minimum=26, color=PALETTE["green"]))
        else: raise ControlError(f"Unsupported scene type: {kind}")
    return image, layouts


def render_frames(plan_path, output_dir, *, audio_path=None, store=None):
    plan_path = Path(plan_path).absolute()
    plan_raw = plan_path.read_bytes()
    plan = json.loads(plan_raw)
    if plan.get("schema") != 1 or not isinstance(plan.get("scenes"), list) or not 1 <= len(plan["scenes"]) <= 150: raise ControlError("Expected storyboard schema 1 with 1–150 scenes")
    if (plan.get("width", WIDTH), plan.get("height", HEIGHT)) != (WIDTH, HEIGHT): raise ControlError("This renderer produces 1920×1080 frames")
    destination = Path(os.path.abspath(output_dir))
    if destination.is_relative_to(PROJECT) and not destination.is_relative_to(PROJECT / ".local"): raise ControlError("Project-local media output belongs under ignored .local")
    for path in [destination, *destination.parents]:
        if path.is_symlink(): raise ControlError("Media output cannot traverse symlinks")
    title = public_text(plan.get("title", ""))
    if not title: raise ControlError("Storyboard title is required")
    resolved = []
    asset_fingerprints = []
    ids = set()
    for source in plan["scenes"]:
        if not isinstance(source, dict) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,80}", source.get("id", "")) or source["id"] in ids: raise ControlError("Scenes need unique safe IDs")
        ids.add(source["id"])
        scene, cover, assets = resolve_scene(source, store=store)
        resolved.append((scene, cover))
        asset_fingerprints.extend(assets)
    audio = audio_path or (plan.get("audio") or {}).get("path")
    audio_info = None
    if audio:
        path = Path(audio).expanduser()
        if not path.is_absolute(): path = plan_path.parent / path
        for candidate in [path, *path.parents]:
            if candidate.is_symlink(): raise ControlError("Recording path must not traverse symlinks")
        if not path.is_file(): raise ControlError("User recording does not exist")
        audio_info = {"path": str(path.resolve()), "sha256": hash_file(path)}
    signature = digest(canonical({"plan": digest(plan_raw), "assets": asset_fingerprints,
                                   "renderer": digest(Path(__file__).read_bytes()), "font": digest(FONT.read_bytes()),
                                   "bold_font": digest(BOLD.read_bytes()), "audio": audio_info}).encode())
    if destination.exists():
        marker_path = safe_path(destination, ".frames-build.json")
        if not marker_path.is_file(): raise ControlError("Output exists without this renderer's marker; use a new directory")
        marker = json.loads(marker_path.read_text())
        if marker.get("signature") != signature: raise ControlError("Inputs changed; render into a new directory")
        for name, fingerprint in marker["files"].items():
            if digest(safe_path(destination, name).read_bytes()) != fingerprint: raise ControlError("Existing rendered asset was modified; preserve it and use a new directory")
        return {"output": str(destination), "frames": str(destination / "frames.json"), "reused": True}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".creator-frames-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        frames, layout_report, image_assets = [], [], []
        for index, (scene, cover) in enumerate(resolved, 1):
            image, boxes = render_scene(scene, cover)
            name = f"frame-{index:03d}.png"
            image.save(stage / name)
            frame = {"id": scene["id"], "image": name, "narration": scene["narration"], "source_refs": scene["source_refs"]}
            for key in ("source_segment_id", "source_block_ids", "narration_block_ids", "visual_purpose"):
                if key in scene: frame[key] = scene[key]
            for key in ("start", "end"):
                if key in scene: frame[key] = scene[key]
            frames.append(frame)
            layout_report.append({"id": scene["id"], "type": scene["type"], "image": name, "boxes": boxes,
                                  "quote_basis": scene.get("quote_basis"), "caption": scene["heading"]})
            image_assets.append({"id": scene["id"], "path": name, "caption": scene["heading"], "source": "local_catalog" if cover else "provided"})
        manifest = {"schema": 1, "title": title, "width": WIDTH, "height": HEIGHT, "fps": 30,
                    "timing_confirmed": plan.get("timing_confirmed") is True, "demo_audio": plan.get("demo_audio") is True,
                    "audio": audio_info, "scenes": frames, "input_signature": signature}
        for key in ("semantic_review", "planning_basis", "document_sha256"):
            if key in plan: manifest[key] = plan[key]
        (stage / "frames.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        (stage / "assets.json").write_text(json.dumps({"schema": 1, "images": image_assets}, ensure_ascii=False, indent=2))
        recording = [f"# {title}：录音与分镜清单", "", "以下文字来自已有文稿或明确选定的引用，不是语音识别结果。可按分镜录音，或录制完整旁白后调整时间轴。", ""]
        for (scene, _), frame in zip(resolved, frames):
            recording += [f"## {scene['id']} · {scene['heading']}", "", f"画面：{frame['image']}", "", scene["narration"], ""]
        (stage / "recording-script.md").write_text("\n".join(recording))
        (stage / "layout-report.json").write_text(json.dumps(layout_report, ensure_ascii=False, indent=2))
        (stage / "gallery.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>分镜预览</title><style>body{font:16px system-ui;background:#F7F9FC;color:#16324F;max-width:1100px;margin:auto;padding:24px}img{width:100%;height:auto}figure{margin:30px 0}figcaption{padding:12px 0}</style><h1>' + html.escape(title) + '</h1><p>检查画面与引用；时间轴确认在录音接入后完成。</p>' + ''.join(f'<figure><img src="{row["image"]}" alt="{html.escape(row["caption"],quote=True)}"><figcaption>{i+1}. {html.escape(row["caption"])}</figcaption></figure>' for i,row in enumerate(layout_report)) + '</html>')
        files = {path.name: digest(path.read_bytes()) for path in stage.iterdir() if path.is_file()}
        (stage / ".frames-build.json").write_text(json.dumps({"schema": 1, "signature": signature, "files": files}, indent=2))
        os.rename(stage, destination)
    return {"output": str(destination), "frames": str(destination / "frames.json"), "scenes": len(frames),
            "status": "frames_ready" if audio else "frames_ready_recording_required", "reused": False}
