"""Offline structural integrity for current records, complete history, and referenced blobs."""
import json
import sqlite3

from .store import ControlError, canonical, digest


def audit_database(connection, load_blob):
    """Does not assert semantic truth or current availability of external originals."""
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ControlError("Database integrity check failed")
        if connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0] != "1":
            raise ControlError("Unsupported database schema")
        def rows(table):
            result = []
            for kind, identity, revision, fingerprint, body in connection.execute(f"SELECT kind,id,revision,digest,body FROM {table}"):
                if digest(body.encode()) != fingerprint:
                    raise ControlError("Database record/history digest mismatch")
                value = json.loads(body)
                if not isinstance(value, dict) or not isinstance(revision, int) or revision < 1:
                    raise ControlError("Invalid stored record shape")
                result.append({"kind": kind, "id": identity, "revision": revision, "digest": fingerprint, "body": body, "data": value})
            return result
        current = {(r["kind"], r["id"]): r for r in rows("records")}
        history_rows = rows("revisions")
    except (sqlite3.DatabaseError, TypeError, IndexError, ValueError) as error:
        raise ControlError(f"Unreadable workflow database: {type(error).__name__}") from error
    history = {(r["kind"], r["id"], r["revision"]): r for r in history_rows}
    grouped = {}
    for row in history_rows:
        grouped.setdefault((row["kind"], row["id"]), []).append(row)
    if set(grouped) != set(current):
        raise ControlError("Current records and revision histories do not match")
    for key, versions in grouped.items():
        versions.sort(key=lambda row: row["revision"])
        if [r["revision"] for r in versions] != list(range(1, len(versions) + 1)):
            raise ControlError("Revision history contains a gap")
        latest = versions[-1]
        if any(current[key][field] != latest[field] for field in ("revision", "digest", "body")):
            raise ControlError("Current record does not equal latest saved revision")

    checked_blobs = set()
    def blob(fingerprint):
        if fingerprint in checked_blobs:
            return
        try:
            raw = load_blob(fingerprint)
        except (OSError, KeyError) as error:
            raise ControlError(f"Referenced blob missing: {fingerprint}") from error
        if digest(raw) != fingerprint:
            raise ControlError("Referenced blob content does not match its identity")
        checked_blobs.add(fingerprint)

    def reference(kind, identity):
        if identity is not None and (kind, identity) not in current:
            raise ControlError(f"Referenced record missing: {kind}/{identity}")

    for row in history_rows:
        kind, data = row["kind"], row["data"]
        for field in {"source_version": ("snapshot_sha256", "units_sha256"), "legacy_note": ("blob",),
                      "draft": ("sha256",), "candidate": ("candidate_blob",)}.get(kind, ()):
            if not data.get(field):
                raise ControlError(f"Missing required object reference: {kind}.{field}")
            blob(data[field])
        if kind in {"release", "preview"}:
            for artifact in data.get("artifacts", {}).values():
                blob(artifact["sha256"])
        if kind == "review":
            for fingerprint in data.get("attachments", {}).values():
                blob(fingerprint)
        for field in ("dependencies", "inputs"):
            snapshot = data.get(field)
            if snapshot is None:
                continue
            if not isinstance(snapshot, dict) or snapshot.get("digest") != digest(canonical({key: value for key, value in snapshot.items() if key != "digest"}).encode()):
                raise ControlError("Dependency snapshot digest mismatch")
            for ref in snapshot.get("records", []):
                reference(ref["kind"], ref["id"])
                saved = history.get((ref["kind"], ref["id"], ref["revision"]))
                if saved is None or saved["digest"] != ref["digest"]:
                    raise ControlError("Dependency points to missing or different historical revision")
        if kind == "source":
            reference("source_version", data.get("active_version_id"))
            for identity in data.get("versions", []): reference("source_version", identity)
        if kind == "source_version": reference("source", data.get("source_id"))
        if kind in {"evidence", "source_mapping"}: reference("source_version", data.get("source_version_id"))
        if kind == "claim":
            for link in data.get("evidence_links", []): reference("evidence", link.get("evidence_id"))
        if kind == "draft":
            for identity in data.get("claim_ids", []): reference("claim", identity)
            reference("draft", data.get("parent_draft_id"))
            if data.get("parent_draft_id") and (data["parent_draft_id"] == row["id"] or
                current[("draft", data["parent_draft_id"])]["data"]["project_id"] != data["project_id"]):
                raise ControlError("Invalid parent draft ownership")
            for ref in data.get("inherited_reviews", []):
                reference("review", ref["id"])
                if current[("review", ref["id"])]["digest"] != ref["digest"] or current[("review", ref["id"])]["data"]["project_id"] != data["project_id"]:
                    raise ControlError("Inherited review digest mismatch")
        if kind == "review_action":
            if data.get("candidate_blob"):
                blob(data["candidate_blob"])
            reference("draft", data.get("draft_id"))
            reference("review_action", data.get("previous_action_id"))
            reference("review", data["review_ref"]["id"])
            if current[("review", data["review_ref"]["id"])]["digest"] != data["review_ref"]["digest"]:
                raise ControlError("Review action identity mismatch")
            if current[("draft", data["draft_id"])]["data"]["project_id"] != data["project_id"] or current[("review", data["review_ref"]["id"])]["data"]["project_id"] != data["project_id"]:
                raise ControlError("Review action project mismatch")
            if data.get("previous_action_id"):
                previous = current[("review_action", data["previous_action_id"])]["data"]
                if previous["draft_id"] != data["draft_id"] or previous["review_ref"] != data["review_ref"]:
                    raise ControlError("Review action history belongs to another item")
        if kind == "review":
            reference(data.get("target_kind"), data.get("target_id"))
            for identity in data.get("supersedes", []): reference("review", identity)
        if kind == "release":
            reference("draft", data.get("draft_id"))
            for identity in data.get("review_ids", []): reference("review", identity)
        if kind == "preview": reference("draft", data.get("draft_id"))
        if kind == "selection": reference("preview", data.get("preview_id"))
        if kind in {"decision", "delivery"}: reference("release", data.get("release_id"))
        if data.get("project_id"): reference("project", data["project_id"])
    return {"records": len(current), "revisions": len(history_rows), "referenced_blobs": len(checked_blobs)}
