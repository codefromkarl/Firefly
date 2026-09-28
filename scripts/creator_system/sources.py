"""Private, versioned source snapshots and replayable short evidence. No network calls."""
from __future__ import annotations

from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile

from creator_system.store import ControlError, canonical, digest, safe_path, utc_now

PARSER_VERSION = "creator-source-1"
MAX_SOURCE_BYTES = 128 * 1024 * 1024


class TextHTML(HTMLParser):
    """Parse inert HTML text; never render it or execute scripts/resources."""
    BLOCKS = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "blockquote", "tr", "pre", "br"}
    HIDDEN = {"script", "style", "noscript", "template", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.parts = []
        self.blocks = []

    def flush(self):
        text = re.sub(r"\s+", " ", "".join(self.parts)).strip()
        if text:
            self.blocks.append(text)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.HIDDEN:
            self.hidden.append(tag)
        if not self.hidden and tag in self.BLOCKS:
            self.flush()

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            return
        if tag in self.BLOCKS:
            self.flush()

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _html(value):
    parser = TextHTML()
    parser.feed(value)
    parser.flush()
    return parser.blocks


def _decode(value):
    # Reject undecodable data rather than create evidence from replacement characters.
    encodings = ("utf-16",) if value.startswith((b"\xff\xfe", b"\xfe\xff")) else ("utf-8-sig", "gb18030")
    for encoding in encodings:
        try:
            return value.decode(encoding)
        except UnicodeError:
            continue
    raise ControlError("Source text encoding unsupported")


def _unit(locator, text):
    return {"locator": locator, "text": text, "text_sha256": digest(text.encode())}


def _paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if p.strip()]


def _epub(value):
    units = []
    try:
        with zipfile.ZipFile(io.BytesIO(value)) as archive:
            infos = archive.infolist()
            if len(infos) > 10000 or any(i.file_size > 32 * 1024 * 1024 for i in infos) or sum(i.file_size for i in infos) > 256 * 1024 * 1024:
                raise ControlError("EPUB exceeds extraction bounds")
            if archive.testzip() or archive.read("mimetype").strip() != b"application/epub+zip":
                raise ControlError("EPUB CRC or mimetype invalid")
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            package_path = container.find(".//{*}rootfile").attrib["full-path"]
            package = ET.fromstring(archive.read(package_path))
            manifest = {x.attrib["id"]: x.attrib for x in package.findall(".//{*}manifest/{*}item")}
            spine = package.findall(".//{*}spine/{*}itemref")
            if not spine:
                raise ControlError("EPUB missing reading-order spine")
            for chapter, item in enumerate(spine, 1):
                meta = manifest[item.attrib["idref"]]
                href = unquote(meta["href"].split("#", 1)[0])
                member = str(PurePosixPath(package_path).parent / href)
                # ZIP member paths are never extracted; still reject ambiguous traversal.
                if href.startswith("/") or ".." in PurePosixPath(member).parts:
                    raise ControlError("Unsupported EPUB member traversal")
                if meta.get("media-type") not in {"application/xhtml+xml", "text/html"}:
                    continue
                for paragraph, text in enumerate(_html(_decode(archive.read(member))), 1):
                    locator = {"kind": "epub", "spine": chapter, "member": member, "paragraph": paragraph}
                    units.append(_unit(locator, text))
            metadata = {"title": [x.text for x in package.findall('.//{http://purl.org/dc/elements/1.1/}title') if x.text],
                        "authors": [x.text for x in package.findall('.//{http://purl.org/dc/elements/1.1/}creator') if x.text]}
    except (zipfile.BadZipFile, KeyError, ET.ParseError, AttributeError, RuntimeError, OSError) as error:
        raise ControlError(f"Unreadable EPUB: {type(error).__name__}") from error
    return units, metadata


def _parse(value, format_name):
    metadata = {}
    if format_name == "epub":
        units, metadata = _epub(value)
    elif format_name in {"html", "htm", "xhtml"}:
        units = [_unit({"kind": "html", "paragraph": i}, text) for i, text in enumerate(_html(_decode(value)), 1)]
    elif format_name in {"txt", "md"}:
        units = [_unit({"kind": format_name, "paragraph": i}, text) for i, text in enumerate(_paragraphs(_decode(value)), 1)]
    elif format_name == "pdf":
        if not shutil.which("pdftotext"):
            return [], {}, "extractor_unavailable"
        with tempfile.TemporaryDirectory(prefix="creator-source-") as directory:
            path = Path(directory) / "source.pdf"
            path.write_bytes(value)
            try:
                output = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"], capture_output=True, timeout=40)
            except subprocess.TimeoutExpired as error:
                raise ControlError("PDF extraction timed out") from error
            if output.returncode:
                raise ControlError("PDF extraction failed")
        units = []
        for page, text in enumerate(output.stdout.decode("utf-8").split("\f"), 1):
            for paragraph, content in enumerate(_paragraphs(text), 1):
                units.append(_unit({"kind": "pdf", "page": page, "paragraph": paragraph}, content))
        if not units:
            return [], {}, "requires_ocr"
    else:
        raise ControlError("Unsupported format; provide EPUB, PDF, HTML, Markdown or TXT")
    return units, metadata, "parsed" if units else "no_text"


def _stable_read(path):
    path = Path(path).expanduser().absolute()
    if not path.is_file():
        raise ControlError("Source file does not exist")
    before = path.stat()
    if before.st_size > MAX_SOURCE_BYTES:
        raise ControlError("Source exceeds 128 MiB input bound")
    content = path.read_bytes()
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ControlError("Source changed during capture; retry after edits finish")
    return path, content


def register_source(store, path, source_id, *, title=None, work_id=None, url=None,
                    capture_scope="full", ocr=False, legacy_note=None):
    """Snapshot a supplied file, return immutable source_version record, map source id separately."""
    store._check("source", source_id)
    if url and (urlsplit(url).scheme not in {"http", "https"} or not urlsplit(url).netloc):
        raise ControlError("Web source requires a public HTTP(S) URL")
    if capture_scope not in {"full", "excerpt", "unknown"}:
        raise ControlError("Capture scope must be full, excerpt or unknown")
    current = next((r for r in store.list("source") if r["id"] == source_id), None)
    if current and current["data"].get("withdrawn"):
        raise ControlError("Source withdrawn; register a new explicit source identity")
    if current and work_id and current["data"].get("work_id") and current["data"]["work_id"] != work_id:
        raise ControlError("Source work mapping conflict")
    if legacy_note and not safe_path(store.vault, legacy_note).is_file():
        raise ControlError("Legacy note does not exist inside vault")
    path, value = _stable_read(path)
    sha = store.blob(value)
    format_name = path.suffix.lower().lstrip(".")
    identity = {"source_id": source_id, "source_sha256": sha, "format": format_name,
                "url": url, "capture_scope": capture_scope, "ocr": bool(ocr)}
    version_id = "SV-" + digest(canonical(identity).encode())
    existing = next((r for r in store.list("source_version") if r["id"] == version_id), None)
    if existing is None:
        try:
            units, metadata, status = _parse(value, format_name)
            error = None
        except ControlError as failure:
            units, metadata, status, error = [], {}, "parse_failed", str(failure)
        data = {**identity, "snapshot_sha256": sha, "format": format_name,
                "title": title or (metadata.get("title") or [path.stem])[0], "authors": metadata.get("authors", []),
                "original_path": str(path), "captured_at": utc_now(), "parser_version": PARSER_VERSION,
                "units_sha256": store.blob(canonical(units).encode()), "unit_count": len(units),
                "parse_status": status, "parse_error": error, "ocr": bool(ocr),
                "uncertainty": "ocr_unverified" if ocr else "semantic_not_reviewed",
                "capture_method": "supplied_snapshot" if url else "local_file", "capture_scope": capture_scope,
                "url": url, "network_fetched_by_system": False}
        existing = store.create("source_version", data, version_id)
    else:
        # The raw byte version is immutable: differing provenance annotations cannot rewrite it.
        if existing["data"]["ocr"] != bool(ocr):
            raise ControlError("Same snapshot already has different OCR provenance; cannot silently relabel")
        if existing["data"]["url"] != url or existing["data"]["capture_scope"] != capture_scope:
            raise ControlError("Same snapshot already has different capture provenance; cannot silently relabel")
    current = next((r for r in store.list("source") if r["id"] == source_id), None)
    location = {"path": str(path), "source_version_id": version_id}
    if current:
        data = dict(current["data"])
        if data.get("withdrawn"):
            raise ControlError("Source withdrawn; register a new explicit source identity")
        if work_id and data.get("work_id") and data["work_id"] != work_id:
            raise ControlError("Source work mapping conflict")
        if location not in data["locations"]:
            data["locations"].append(location)
        if version_id not in data["versions"]:
            data["versions"].append(version_id)
        data["active_version_id"] = version_id
        if work_id and not data.get("work_id"):
            data["work_id"] = work_id
        store.update("source", source_id, data, current["digest"])
    else:
        store.create("source", {"title": title or existing["data"]["title"], "work_id": work_id,
                               "locations": [location], "versions": [version_id], "active_version_id": version_id, "withdrawn": False}, source_id)
    if legacy_note:
        map_legacy_source(store, legacy_note, version_id)
    store.event("source_registered", {"source_id": source_id, "source_version_id": version_id})
    return existing


def _units(store, version_id, *, reparse=False):
    record = store.get("source_version", version_id)
    data = record["data"]
    raw = store.read_blob(data["snapshot_sha256"])
    identity = {k: data[k] for k in ("source_id", "source_sha256", "format", "url", "capture_scope", "ocr")}
    if digest(raw) != data["source_sha256"] or version_id != "SV-" + digest(canonical(identity).encode()):
        raise ControlError("Source version and snapshot do not match")
    if data["parser_version"] != PARSER_VERSION:
        raise ControlError("Parser version changed; old evidence needs its original parser")
    units = json.loads(store.read_blob(data["units_sha256"]))
    if data["parse_status"] != "parsed":
        raise ControlError(f"Source not readable: {data['parse_status']}")
    if reparse:
        parsed, _, status = _parse(raw, data["format"])
        if status != "parsed" or canonical(parsed) != canonical(units):
            raise ControlError("Snapshot reparse differs from saved extraction")
    return record, units


def list_units(store, source_version_id):
    _, units = _units(store, source_version_id)
    return [{"locator": u["locator"], "text_sha256": u["text_sha256"], "preview": u["text"][:240]} for u in units]


def _locate(units, locator):
    if isinstance(locator, str):
        try:
            locator = json.loads(locator)
        except json.JSONDecodeError as error:
            raise ControlError("Locator must be a JSON object returned by list_units") from error
    for i, unit in enumerate(units):
        if unit["locator"] == locator:
            return i, unit
    raise ControlError("Exact source locator not found; chapter/page/member must all match")


def read_source(store, source_version_id, locator, *, context=1, max_chars=1200):
    if not isinstance(context, int) or not 0 <= context <= 3 or not isinstance(max_chars, int) or not 1 <= max_chars <= 4000:
        raise ControlError("Read bounds: context 0..3, max_chars 1..4000")
    record, units = _units(store, source_version_id)
    index, unit = _locate(units, locator)
    return {"source_version_id": source_version_id, "locator": unit["locator"], "text_sha256": unit["text_sha256"],
            "text": unit["text"][:max_chars], "truncated": len(unit["text"]) > max_chars,
            "context": [{"locator": u["locator"], "text": u["text"][:240]} for i, u in enumerate(units) if abs(i - index) <= context and i != index],
            "parser_version": record["data"]["parser_version"], "uncertainty": record["data"]["uncertainty"]}


def search(store, query, *, source_version_id=None, topk=5):
    if not query.strip() or not 1 <= topk <= 20:
        raise ControlError("Search needs non-empty query and topk 1..20")
    terms = query.casefold().split()
    versions = [store.get("source_version", source_version_id)] if source_version_id else store.list("source_version")
    if source_version_id is None:
        active = {row["data"].get("active_version_id") for row in store.list("source") if not row["data"].get("withdrawn")}
        versions = [row for row in versions if row["id"] in active]
    results = []
    for record in versions:
        if record["data"]["parse_status"] != "parsed":
            continue
        _, units = _units(store, record["id"])
        state = source_status(store, record["id"])
        for unit in units:
            score = sum(unit["text"].casefold().count(term) for term in terms)
            if score:
                results.append({"source_version_id": record["id"], "locator": unit["locator"],
                                "text_sha256": unit["text_sha256"], "preview": unit["text"][:240], "score": score,
                                "source_state": {key: state[key] for key in ("withdrawn", "active_version_changed", "current_source_changed", "current_source_unavailable", "web_live_status")},
                                "ranking_meaning": "keyword_frequency_not_truth"})
    return sorted(results, key=lambda r: (-r["score"], r["source_version_id"], canonical(r["locator"])))[:topk]


def create_evidence(store, source_version_id, locator, *, quote=None):
    record, units = _units(store, source_version_id, reparse=True)
    _, unit = _locate(units, locator)
    quote = unit["text"][:240] if quote is None else quote
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 240 or quote not in unit["text"]:
        raise ControlError("Evidence quote must literally match this unit and contain 1..240 characters")
    text_sha = digest(quote.encode())
    identity = {"source_version_id": source_version_id, "locator": unit["locator"], "text_sha256": text_sha}
    evidence_id = "EV-" + digest(canonical(identity).encode())
    existing = next((r for r in store.list("evidence") if r["id"] == evidence_id), None)
    if existing:
        replay_evidence(store, evidence_id)
        return existing
    return store.create("evidence", {**identity, "quote": quote, "unit_sha256": unit["text_sha256"],
                       "parser_version": record["data"]["parser_version"], "uncertainty": record["data"]["uncertainty"],
                       "extracted_at": utc_now(), "semantic_review": "not_reviewed"}, evidence_id)


def source_status(store, source_version_id):
    record = store.get("source_version", source_version_id)
    source = store.get("source", record["data"]["source_id"])
    store.read_blob(record["data"]["snapshot_sha256"])
    paths = {record["data"]["original_path"]}
    paths.update(x["path"] for x in source["data"]["locations"] if x["source_version_id"] == source_version_id)
    statuses = []
    for path in sorted(paths):
        try:
            _, raw = _stable_read(path)
            status = "unchanged" if digest(raw) == record["data"]["source_sha256"] else "current_source_changed"
        except (ControlError, OSError):
            status = "missing_or_unreadable"
        statuses.append({"path": path, "status": status})
    checks = [row for row in store.list("receipt") if row["data"].get("type") == "web_check" and row["data"].get("source_version_id") == source_version_id]
    checks.sort(key=lambda row: row["data"].get("checked_at", ""))
    web_check = checks[-1]["data"] if checks else None
    return {"source_version_id": source_version_id, "source_id": source["id"], "withdrawn": source["data"].get("withdrawn", False),
            "active_version_changed": source["data"].get("active_version_id") != source_version_id,
            "current_source_changed": any(x["status"] == "current_source_changed" for x in statuses),
            "current_source_unavailable": not any(x["status"] == "unchanged" for x in statuses),
            "locations": statuses, "snapshot_available": True, "parse_status": record["data"]["parse_status"],
            "uncertainty": record["data"]["uncertainty"],
            "web_live_status": web_check["status"] if web_check else ("not_checked" if record["data"]["url"] else "not_applicable"),
            "web_checked_at": web_check.get("checked_at") if web_check else None,
            "web_body_unchanged": "not_verified_by_head_probe"}


def replay_evidence(store, evidence_id):
    evidence = store.get("evidence", evidence_id)["data"]
    record, units = _units(store, evidence["source_version_id"], reparse=True)
    _, unit = _locate(units, evidence["locator"])
    identity = {k: evidence[k] for k in ("source_version_id", "locator", "text_sha256")}
    if evidence_id != "EV-" + digest(canonical(identity).encode()) or digest(evidence["quote"].encode()) != evidence["text_sha256"] or unit["text_sha256"] != evidence["unit_sha256"] or evidence["quote"] not in unit["text"] or evidence["parser_version"] != record["data"]["parser_version"]:
        raise ControlError("Evidence identity, text or source version mismatch")
    status = source_status(store, evidence["source_version_id"])
    return {"valid": True, "evidence_id": evidence_id, **evidence, "source_status": status,
            "current_source_changed": status["current_source_changed"], "meaning": "literal_replay_not_semantic_truth"}


def map_legacy_source(store, note_path, source_version_id, *, legacy_verification=None):
    store.get("source_version", source_version_id)
    path = safe_path(store.vault, note_path)
    if not path.is_file():
        raise ControlError("Legacy note does not exist inside vault")
    content = path.read_bytes()
    data = {"note_path": note_path, "note_sha256": digest(content), "source_version_id": source_version_id,
            "legacy_verification": legacy_verification, "verification": "pending_review", "note_unchanged": True}
    mapping_id = "MAP-" + digest(canonical(data).encode())
    existing = next((r for r in store.list("source_mapping") if r["id"] == mapping_id), None)
    return existing or store.create("source_mapping", data, mapping_id)


def withdraw_source(store, source_id, reason):
    """Explicit withdrawal invalidates downstream current-use decisions, not historical replay."""
    if not isinstance(reason, str) or not reason.strip():
        raise ControlError("Withdrawal reason required")
    record = store.get("source", source_id)
    data = {**record["data"], "withdrawn": True, "withdrawal_reason": reason, "withdrawn_at": utc_now()}
    result = store.update("source", source_id, data, record["digest"])
    store.event("source_withdrawn", {"source_id": source_id, "reason": reason})
    return result
