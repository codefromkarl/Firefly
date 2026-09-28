"""Transactional local records with immutable history and content-addressed blobs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from datetime import datetime, timezone
import uuid


class ControlError(ValueError):
    """Expected workflow condition, safe to display without a traceback."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def safe_path(root: Path, relative: str) -> Path:
    """A managed path must remain inside root and have no symlink components."""
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ControlError("Expected a non-empty relative path inside the vault")
    root = Path(os.path.abspath(Path(root).expanduser()))
    candidate = root / rel
    for node in [candidate, *candidate.parents]:
        if node.is_symlink():
            raise ControlError(f"Symlink managed path refused: {node.name}")
    return candidate


class Store:
    def __init__(self, vault):
        self.vault = Path(os.path.abspath(Path(vault).expanduser()))
        project = Path(__file__).resolve().parents[2]
        if self.vault.is_relative_to(project) and not self.vault.is_relative_to(project / ".local"):
            raise ControlError("Project-local private vaults must be under .local")
        self.root = safe_path(self.vault, ".creator-system")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.objects = safe_path(self.vault, ".creator-system/objects")
        self.objects.mkdir(exist_ok=True, mode=0o700)
        database = safe_path(self.vault, ".creator-system/state.sqlite3")
        self.db = sqlite3.connect(database, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS records (
          kind TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
          digest TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS revisions (
          kind TEXT NOT NULL, id TEXT NOT NULL, revision INTEGER NOT NULL,
          digest TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(kind,id,revision));
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT OR IGNORE INTO metadata VALUES ('schema_version','1');
        """)
        version = self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0]
        if version != "1":
            raise ControlError("Unsupported store schema; do not silently migrate")
        self.db.commit()

    def close(self):
        self.db.close()

    @staticmethod
    def _check(kind, record_id):
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", kind):
            raise ControlError("Invalid record kind")
        if not isinstance(record_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,180}", record_id):
            raise ControlError("Invalid stable record id")

    @staticmethod
    def _record(row):
        if digest(row["body"].encode()) != row["digest"]:
            raise ControlError("Record digest mismatch; restore or investigate corruption")
        return {"kind": row["kind"], "id": row["id"], "revision": row["revision"],
                "digest": row["digest"], "data": json.loads(row["body"])}

    def get(self, kind, record_id, revision=None):
        self._check(kind, record_id)
        if revision is None:
            row = self.db.execute("SELECT * FROM records WHERE kind=? AND id=?", (kind, record_id)).fetchone()
        else:
            row = self.db.execute("SELECT * FROM revisions WHERE kind=? AND id=? AND revision=?", (kind, record_id, revision)).fetchone()
        if row is None:
            raise ControlError(f"Unknown {kind}: {record_id}")
        return self._record(row)

    def list(self, kind):
        return [self._record(row) for row in self.db.execute("SELECT * FROM records WHERE kind=? ORDER BY id", (kind,))]

    def create(self, kind, data, record_id=None):
        record_id = record_id or uuid.uuid4().hex
        self._check(kind, record_id)
        body = canonical(data)
        fingerprint = digest(body.encode())
        try:
            with self.db:
                self.db.execute("INSERT INTO records VALUES (?,?,?,?,?)", (kind, record_id, 1, fingerprint, body))
                self.db.execute("INSERT INTO revisions VALUES (?,?,?,?,?,?)", (kind, record_id, 1, fingerprint, body, utc_now()))
        except sqlite3.IntegrityError as error:
            raise ControlError(f"Record already exists: {kind}/{record_id}") from error
        return self.get(kind, record_id)

    def update(self, kind, record_id, data, expected_digest):
        self._check(kind, record_id)
        if kind in {"source_version", "evidence", "review", "decision", "receipt", "event", "preview", "review_action"}:
            raise ControlError(f"{kind} records are immutable; create a new record")
        body = canonical(data)
        fingerprint = digest(body.encode())
        try:
            self.db.execute("BEGIN IMMEDIATE")
            current = self.get(kind, record_id)
            if current["digest"] != expected_digest:
                raise ControlError("Revision conflict; reload and merge, do not overwrite")
            if fingerprint != expected_digest:
                rev = current["revision"] + 1
                self.db.execute("UPDATE records SET revision=?,digest=?,body=? WHERE kind=? AND id=?", (rev, fingerprint, body, kind, record_id))
                self.db.execute("INSERT INTO revisions VALUES (?,?,?,?,?,?)", (kind, record_id, rev, fingerprint, body, utc_now()))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        return self.get(kind, record_id)

    def blob(self, value: bytes):
        fingerprint = digest(value)
        target = safe_path(self.root, f"objects/{fingerprint}")
        if target.exists():
            if digest(target.read_bytes()) != fingerprint:
                raise ControlError("Stored object corrupted")
        else:
            staging = safe_path(self.root, f"staging/{uuid.uuid4().hex}")
            staging.parent.mkdir(exist_ok=True, mode=0o700)
            try:
                with staging.open("xb") as stream:
                    stream.write(value)
                    stream.flush()
                    os.fsync(stream.fileno())
                # A crash cannot expose a partial object under its permanent hash.
                # Link is exclusive: a concurrent writer cannot replace an object.
                os.link(staging, target)
            except FileExistsError:
                if digest(target.read_bytes()) != fingerprint:
                    raise ControlError("Stored object conflict")
            finally:
                staging.unlink(missing_ok=True)
        return fingerprint

    def read_blob(self, fingerprint):
        if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
            raise ControlError("Invalid object hash")
        value = safe_path(self.root, f"objects/{fingerprint}").read_bytes()
        if digest(value) != fingerprint:
            raise ControlError("Stored object corrupted")
        return value

    def event(self, action, data):
        return self.create("event", {"action": action, "at": utc_now(), **data})
