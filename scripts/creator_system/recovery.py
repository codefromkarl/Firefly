"""Recover source bytes from a verified snapshot without changing source authority."""
import os
from pathlib import Path
import re
import tempfile

from .store import ControlError, canonical, digest, safe_path, utc_now
from .sources import source_status


def recover_source(store, source_version_id, destination=None):
    version = store.get("source_version", source_version_id)
    data = version["data"]
    source = store.get("source", data["source_id"])
    raw = store.read_blob(data["snapshot_sha256"])
    if digest(raw) != data["source_sha256"]:
        raise ControlError("Source byte identity does not match saved version")
    extension = data["format"] if re.fullmatch(r"[a-z0-9]{1,16}", data["format"]) else "bin"
    relative = destination or f".creator-system/recovered/{source_version_id}/{source['id']}.{extension}"
    target = safe_path(store.vault, relative)
    # User-named files can be recovered only to an explicit new path, never replaced.
    if target.exists():
        if not target.is_file() or digest(target.read_bytes()) != data["source_sha256"]:
            raise ControlError("Recovery target already exists with different content; preserve it and choose a new path")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".creator-recover-", dir=target.parent, delete=False) as stream:
                staged = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(staged, target)
        except FileExistsError:
            if digest(target.read_bytes()) != data["source_sha256"]:
                raise ControlError("Recovery target appeared with different bytes")
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    identity = {"source_version_id": source_version_id, "path": str(target), "sha256": data["source_sha256"]}
    location = {"path": str(target), "source_version_id": source_version_id}
    if location not in source["data"]["locations"]:
        updated = {**source["data"], "locations": [*source["data"]["locations"], location]}
        store.update("source", source["id"], updated, source["digest"])
    receipt_id = "RECOVER-" + digest(canonical(identity).encode())
    previous = next((row for row in store.list("receipt") if row["id"] == receipt_id), None)
    receipt = previous or store.create("receipt", {"type": "source_recovery", **identity, "at": utc_now(),
                                                  "active_version_changed": False, "withdrawal_overridden": False,
                                                  "original_external_file_modified": False}, receipt_id)
    return {"receipt": receipt, "path": str(target), "status": source_status(store, source_version_id),
            "meaning": "Recovered bytes and registered location only; source/author decisions are unchanged."}
