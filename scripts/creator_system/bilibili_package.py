"""Read an exact local Bilibili package; never certify content or platform acceptance."""
import json
import re

from .store import ControlError, digest, safe_path


MARKER = ".creator-bilibili.json"
BASE_FILES = {"article.md", "title.txt", "bilibili.html", "bilibili.txt", "asset-order.json", "delivery.json"}


def read_package(directory, draft_sha256):
    if not safe_path(directory, MARKER).is_file():
        raise ControlError("Bilibili package required; generate it with creator:system preview")
    marker_bytes = safe_path(directory, MARKER).read_bytes()
    marker = json.loads(marker_bytes)
    if marker.get("schema") != 1 or marker.get("tool") != "firefly-creator-bilibili":
        raise ControlError("Expected Bilibili export provenance marker")
    inputs = marker.get("inputs", {})
    identity = {"article": inputs.get("article"), "assets": inputs.get("assets")}
    signature = digest(json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode())
    if marker.get("input_signature") != signature or identity["article"] != draft_sha256:
        raise ControlError("Bilibili package input does not match the exact registered draft/signature")
    if identity["assets"] is not None and not re.fullmatch(r"[0-9a-f]{64}", str(identity["assets"])):
        raise ControlError("Invalid Bilibili asset identity")

    def read(name):
        raw = safe_path(directory, name).read_bytes()
        if marker.get("hashes", {}).get(name) != digest(raw):
            raise ControlError(f"Bilibili artifact changed after export: {name}")
        return raw

    values = {name: read(name) for name in sorted(BASE_FILES)}
    order = json.loads(values["asset-order.json"])
    images = order.get("images")
    if order.get("schema") != 1 or not isinstance(images, list) or len(images) > 30:
        raise ControlError("Invalid Bilibili image order")
    names, ids = set(), set()
    for index, item in enumerate(images, 1):
        name, identity = item.get("file", ""), item.get("id")
        if not re.fullmatch(r"images/[A-Za-z0-9_-]+\.(?:png|jpg)", name) or name in names or not identity or identity in ids or item.get("order") != index:
            raise ControlError("Invalid Bilibili image path, identity or sequence")
        raw = read(name)
        if item.get("sha256") != digest(raw):
            raise ControlError("Bilibili image order hash differs from the exported image")
        values[name] = raw
        names.add(name)
        ids.add(identity)
    delivery = json.loads(values["delivery.json"])
    expected = {"schema": 1, "status": "local_ready", "publication": "not_published",
                "platform_preview": "pending", "platform_compatibility": "not_verified",
                "body": "bilibili.html", "fallback": "bilibili.txt", "image_order": "asset-order.json",
                "images": len(images)}
    if any(delivery.get(key) != value for key, value in expected.items()):
        raise ControlError("Bilibili delivery metadata does not describe a local preview package")
    if values["title.txt"].decode("utf8") != delivery.get("title", "") + "\n":
        raise ControlError("Bilibili title differs from delivery metadata")
    # Old unselected images may remain on disk. Only the current upload list is released.
    values[MARKER] = marker_bytes
    return values
