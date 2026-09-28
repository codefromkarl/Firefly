"""Verified local backups and restore-to-new-directory; no scheduler or cloud service."""
import json
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from contextlib import contextmanager

from .store import ControlError, canonical, digest, safe_path, utc_now
from .integrity import audit_database

DB_NAME = ".creator-system/state.sqlite3"
PROJECT = Path(__file__).resolve().parents[2]


def _private_destination(value):
    destination = Path(os.path.abspath(Path(value).expanduser()))
    if destination.is_relative_to(PROJECT) and not destination.is_relative_to(PROJECT / ".local"):
        raise ControlError("Project-local backups and restored vaults must stay under ignored .local")
    for node in [destination, *destination.parents]:
        if node.is_symlink():
            raise ControlError("Private recovery paths must not traverse symlinks")
    return destination


def _files(root):
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ControlError("Backup refuses symlinks; choose explicit source files")
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel.startswith(".creator-system/staging/"):
                continue  # Uncommitted temporary blobs are never referenced by records.
            if rel in {DB_NAME + suffix for suffix in ("", "-journal", "-wal", "-shm")}:
                continue
            result.append((rel, path))
    return result


@contextmanager
def _archive_snapshot(source):
    """One stable private archive copy; later pathname replacement cannot affect restore."""
    if hasattr(source, "read"):
        source.seek(0)
        yield source
        return
    with open(source, "rb") as original, tempfile.TemporaryFile() as saved:
        before = os.fstat(original.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 8 * 1024**3:
            raise ControlError("Backup must be a regular archive within the restore size limit")
        for chunk in iter(lambda: original.read(1024 * 1024), b""):
            saved.write(chunk)
        after = os.fstat(original.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ControlError("Backup archive changed while being captured")
        saved.seek(0)
        yield saved


def _archive_hash(stream):
    stream.seek(0)
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""): value.update(chunk)
    stream.seek(0)
    return value.hexdigest()


def verify_backup(filename):
    """Verify all members, not just a ZIP CRC. Never extract arbitrary ZIP paths."""
    with _archive_snapshot(filename) as saved, zipfile.ZipFile(saved) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise ControlError("Invalid backup manifest or duplicate members")
        if sum(info.file_size for info in infos) > 8 * 1024**3:
            raise ControlError("Backup exceeds the local restore size limit")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("schema") != 1 or not isinstance(manifest.get("files"), dict):
            raise ControlError("Unsupported backup schema")
        expected = {f"vault/{name}" for name in manifest["files"]} | {"manifest.json"}
        if set(names) != expected:
            raise ControlError("Backup members do not match manifest")
        for info in infos:
            if info.filename == "manifest.json":
                continue
            if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                raise ControlError("Symlink/encrypted archive entries are unsupported")
            rel = info.filename.removeprefix("vault/")
            if "\\" in rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
                raise ControlError("Unsafe backup path")
            data = archive.read(info)
            if digest(data) != manifest["files"][rel]["sha256"] or len(data) != manifest["files"][rel]["bytes"]:
                raise ControlError(f"Backup content mismatch: {rel}")
            if rel.startswith(".creator-system/objects/") and Path(rel).name != digest(data):
                raise ControlError("Backup contains a corrupted content-addressed object")
        if DB_NAME not in manifest["files"]:
            raise ControlError("Backup must contain workflow database")
        with tempfile.TemporaryDirectory(prefix="creator-integrity-") as tmp:
            database_path = Path(tmp) / "state.sqlite3"
            database_path.write_bytes(archive.read(f"vault/{DB_NAME}"))
            database = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
            try:
                manifest["integrity"] = audit_database(database, lambda fingerprint: archive.read(f"vault/.creator-system/objects/{fingerprint}"))
            finally:
                database.close()
        manifest["archive_sha256"] = _archive_hash(saved)
    return manifest


def backup_vault(store, destination, *, purpose="manual_backup"):
    if purpose not in {"manual_backup", "local_recovery_drill"}:
        raise ControlError("Unknown backup purpose")
    destination = _private_destination(destination)
    if destination.is_relative_to(store.vault):
        raise ControlError("Backup destination must be outside the vault")
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    filename = destination / f"creator-{uuid.uuid4().hex}.zip"
    before = [(row["kind"], row["id"], row["digest"]) for row in store.db.execute("SELECT kind,id,digest FROM records ORDER BY kind,id")]
    originals = _files(store.vault)
    manifest = {"schema": 1, "created_at": utc_now(), "files": {}, "purpose": purpose,
                "meaning": "Local snapshot; a different directory does not prove an independent device."}
    with tempfile.TemporaryDirectory(prefix="creator-backup-") as tmp:
        db_copy = Path(tmp) / "state.sqlite3"
        connection = sqlite3.connect(db_copy)
        try:
            store.db.backup(connection)
        finally:
            connection.close()
        with zipfile.ZipFile(filename, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            filename.chmod(0o600)
            for rel, path in [*originals, (DB_NAME, db_copy)]:
                before_stat = path.stat()
                data = path.read_bytes()
                after_stat = path.stat()
                if (before_stat.st_size, before_stat.st_mtime_ns) != (after_stat.st_size, after_stat.st_mtime_ns):
                    raise ControlError("Source changed during backup; incomplete archive is not verified")
                manifest["files"][rel] = {"sha256": digest(data), "bytes": len(data)}
                archive.writestr(f"vault/{rel}", data)
            after = [(row["kind"], row["id"], row["digest"]) for row in store.db.execute("SELECT kind,id,digest FROM records ORDER BY kind,id")]
            if before != after or [rel for rel, _ in _files(store.vault)] != [rel for rel, _ in originals]:
                raise ControlError("Vault changed during backup; retry a stable snapshot")
            for rel, path in originals:
                if digest(path.read_bytes()) != manifest["files"][rel]["sha256"]:
                    raise ControlError("Vault file changed during backup; no verified receipt created")
            archive.writestr("manifest.json", canonical(manifest))
    verified = verify_backup(filename)
    return store.create("backup", {"path": str(filename), "sha256": verified["archive_sha256"], "purpose": purpose,
                                  "files": len(manifest["files"]), "verified_at": utc_now(),
                                  "restore_tested": False, "independent_device": "unknown",
                                  "filesystem_relation": "same_filesystem" if destination.stat().st_dev == store.vault.stat().st_dev else "different_filesystem",
                                  "integrity": verified["integrity"]})


def restore_backup(filename, destination):
    destination = _private_destination(destination)
    if destination.exists():
        raise ControlError("Restore requires a new directory; existing vaults are never overwritten")
    with _archive_snapshot(filename) as saved:
        manifest = verify_backup(saved)
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".creator-restore-", dir=destination.parent))
        saved.seek(0)
        with zipfile.ZipFile(saved) as archive:
            expected = {f"vault/{name}" for name in manifest["files"]} | {"manifest.json"}
            if len(archive.namelist()) != len(expected) or set(archive.namelist()) != expected:
                raise ControlError("Archive members changed after verification")
            for rel in manifest["files"]:
                target = safe_path(stage, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                value = archive.read(f"vault/{rel}")
                metadata = manifest["files"][rel]
                if digest(value) != metadata["sha256"] or len(value) != metadata["bytes"]:
                    raise ControlError("Archive member changed after verification")
                with target.open("xb") as stream:
                    stream.write(value)
        database = sqlite3.connect(stage / DB_NAME)
        try:
            integrity = audit_database(database, lambda fingerprint: safe_path(stage, f".creator-system/objects/{fingerprint}").read_bytes())
        finally:
            database.close()
        if destination.exists():
            raise ControlError("Restore destination appeared during restore")
        os.rename(stage, destination)
    return {"destination": str(destination), "files": len(manifest["files"]),
            "verified": True, "archive_sha256": manifest["archive_sha256"], "integrity": integrity,
            "purpose": manifest.get("purpose", "manual_backup"),
            "external_original_paths": "use source-recover to explicitly restore/rebind verified snapshots when needed"}
