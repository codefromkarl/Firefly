"""Explicit local workflow records; never executes evidence, models, or delivery tools."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from .store import ControlError, canonical, digest, safe_path, utc_now

RELATIONS = {"supports", "contradicts", "limits", "unrelated"}
CLAIM_TYPES = {"paraphrase", "quotation", "empirical", "synthesis", "personal_judgment"}
REVIEW_CONCLUSIONS = {"pass", "needs_review", "fail"}


def _hash(value):
    return digest(canonical(value).encode())


def _body(text):
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    if text.startswith("---\n"):
        match = re.search(r"\n---(?:\n|$)", text[4:])
        if not match:
            raise ControlError("Unclosed draft frontmatter")
        text = text[4 + match.end():]
    return text.strip() + "\n"


class Workflow:
    def __init__(self, store):
        self.store = store

    def create_project(self, project_id, goal, scope, max_attempts=3):
        if not isinstance(goal, str) or not goal.strip():
            raise ControlError("Project goal is required")
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or not 1 <= max_attempts <= 100:
            raise ControlError("max_attempts must be 1..100")
        if not isinstance(scope, dict):
            raise ControlError("Project scope must be an object")
        scope = {"read_paths": scope.get("read_paths", []), "write_paths": scope.get("write_paths", []),
                 "tools": scope.get("tools", []), "network": scope.get("network", False)}
        for field in ("read_paths", "write_paths"):
            if not isinstance(scope[field], list) or not scope[field]:
                raise ControlError(f"Explicit {field} are required")
            for relative in scope[field]:
                if not isinstance(relative, str) or not relative:
                    raise ControlError("Scope paths must be relative strings")
                if relative != ".":
                    safe_path(self.store.vault, relative)
        if not isinstance(scope["tools"], list) or not all(isinstance(x, str) and x for x in scope["tools"]):
            raise ControlError("Scope tools must be an explicit list")
        if not isinstance(scope["network"], bool):
            raise ControlError("Scope network must be boolean")
        return self.store.create("project", {"goal": goal, "scope": scope, "max_attempts": max_attempts,
                                            "created_at": utc_now(), "status": "defined"}, project_id)

    def _path(self, project_id, relative, mode="read"):
        project = self.store.get("project", project_id)
        target = safe_path(self.store.vault, relative)
        allowed = project["data"]["scope"][f"{mode}_paths"]
        for prefix in allowed:
            root = self.store.vault if prefix == "." else safe_path(self.store.vault, prefix)
            if target == root or root in target.parents:
                return target
        raise ControlError(f"Path outside project {mode} scope: {relative}")

    @staticmethod
    def _owned_by(project_id, record):
        if record["kind"] == "project":
            return record["id"] == project_id
        if record["kind"] in {"claim", "draft", "review", "release", "decision", "run", "delivery", "preview", "selection", "review_action"}:
            return record["data"].get("project_id") == project_id
        return True  # Registered sources and evidence may deliberately be shared.

    def _ref(self, kind, record_id):
        record = self.store.get(kind, record_id)
        return {key: record[key] for key in ("kind", "id", "revision", "digest")}

    def snapshot(self, project_id, note_paths=None, records=None):
        notes = []
        for relative in sorted(set(note_paths or [])):
            path = self._path(project_id, relative)
            if not path.is_file():
                raise ControlError(f"Input is not a readable file: {relative}")
            notes.append({"path": relative, "sha256": digest(path.read_bytes())})
        refs = [self._ref("project", project_id)]
        for ref in records or []:
            if not isinstance(ref, dict) or not {"kind", "id"} <= ref.keys():
                raise ControlError("Record inputs need kind and id")
            record = self.store.get(ref["kind"], ref["id"])
            if not self._owned_by(project_id, record):
                raise ControlError("Project-owned input belongs to another project")
            resolved = self._ref(ref["kind"], ref["id"])
            if resolved not in refs:
                refs.append(resolved)
        refs.sort(key=lambda x: (x["kind"], x["id"]))
        result = {"project_id": project_id, "notes": notes, "records": refs}
        result["digest"] = _hash(result)
        return result

    def _snapshot_issues(self, snapshot, seen=None):
        seen = set() if seen is None else seen
        issues = []
        if not isinstance(snapshot, dict) or snapshot.get("digest") != _hash({k: v for k, v in snapshot.items() if k != "digest"}):
            return ["Input snapshot digest mismatch"]
        for note in snapshot.get("notes", []):
            try:
                current = self._path(snapshot["project_id"], note["path"])
                if digest(current.read_bytes()) != note["sha256"]:
                    issues.append(f"note_changed:{note['path']}")
            except (ControlError, OSError) as error:
                issues.append(f"note_unavailable:{note['path']}:{error}")
        for ref in snapshot.get("records", []):
            key = (ref["kind"], ref["id"], ref["digest"])
            if key in seen:
                continue
            seen.add(key)
            try:
                current = self.store.get(ref["kind"], ref["id"])
                if not self._owned_by(snapshot["project_id"], current):
                    issues.append(f"project_ownership_mismatch:{ref['kind']}/{ref['id']}")
                if current["digest"] != ref["digest"]:
                    issues.append(f"record_changed:{ref['kind']}/{ref['id']}")
                # Keep traversing the exact recorded revision, not a changed object's new dependencies.
                saved = self.store.get(ref["kind"], ref["id"], ref["revision"])
                if saved["digest"] != ref["digest"]:
                    issues.append(f"record_history_mismatch:{ref['kind']}/{ref['id']}")
                    continue
                issues.extend(self._record_issues(saved, seen))
            except (ControlError, OSError) as error:
                issues.append(f"record_unavailable:{ref['kind']}/{ref['id']}:{error}")
        return list(dict.fromkeys(issues))

    def _record_issues(self, record, seen=None):
        data = record["data"]
        issues = []
        if data.get("withdrawn") or data.get("status") == "withdrawn":
            issues.append(f"withdrawn:{record['kind']}/{record['id']}")
        if record["kind"] in {"evidence", "source_version"}:
            from .sources import replay_evidence, source_status
            status = replay_evidence(self.store, record["id"]) if record["kind"] == "evidence" else source_status(self.store, record["id"])
            source = status.get("source_status", status)
            invalid = (record["kind"] == "evidence" and not status.get("valid", False)) or not source.get("snapshot_available", False) or source.get("parse_status") != "parsed"
            invalid |= any(source.get(key, False) for key in ("withdrawn", "active_version_changed", "current_source_changed", "current_source_unavailable"))
            invalid |= source.get("web_live_status") == "unavailable"
            if invalid:
                issues.append(f"source_invalid:{record['kind']}/{record['id']}:{canonical(source)}")
        for key in ("dependencies", "inputs"):
            if key in data:
                issues.extend(self._snapshot_issues(data[key], seen))
        if record["kind"] == "decision":
            if data.get("review_frontier") != self._decision_frontier(data["release_id"]):
                issues.append("author_decision_predates_review_objection_or_resolution")
        if record["kind"] == "review":
            for fingerprint in data.get("attachments", {}).values():
                try:
                    self.store.read_blob(fingerprint)
                except (ControlError, OSError) as error:
                    issues.append(f"review_attachment_unavailable:{error}")
        if record["kind"] == "draft":
            for ref in data.get("inherited_reviews", []):
                try:
                    earlier = self.store.get("review", ref["id"])
                    if earlier["digest"] != ref["digest"] or earlier["data"]["project_id"] != data["project_id"]:
                        issues.append("inherited_review_identity_mismatch")
                except ControlError as error:
                    issues.append(f"inherited_review_unavailable:{error}")
        if record["kind"] == "review_action" and data.get("candidate_blob"):
            try:
                self.store.read_blob(data["candidate_blob"])
            except (ControlError, OSError) as error:
                issues.append(f"action_candidate_unavailable:{error}")
        if record["kind"] == "preview":
            try:
                directory = self._path(data["project_id"], data["artifact_dir"], "write")
                for name, artifact in data["artifacts"].items():
                    self.store.read_blob(artifact["sha256"])
                    if digest(safe_path(directory, name).read_bytes()) != artifact["sha256"]:
                        issues.append(f"preview_artifact_changed:{name}")
            except (ControlError, OSError) as error:
                issues.append(f"preview_unavailable:{error}")
        if record["kind"] == "release":
            if data.get("format") != "bilibili":
                issues.append("retired_release_format:prepare_a_current_bilibili_package")
            if data.get("format") == "bilibili":
                try:
                    directory = self._path(data["project_id"], data["artifact_dir"], "write")
                    for name, artifact in data["artifacts"].items():
                        if digest(safe_path(directory, name).read_bytes()) != artifact["sha256"]:
                            issues.append(f"delivery_artifact_changed:{name}")
                except (ControlError, OSError) as error:
                    issues.append(f"delivery_directory_unavailable:{error}")
            if ("skip_live_reviews",) not in (seen or set()):
                targets = [("release", record["id"]), ("draft", data["draft_id"])]
                draft = self.store.get("draft", data["draft_id"])
                targets.extend(("claim", claim_id) for claim_id in draft["data"]["claim_ids"])
                outstanding = self._outstanding_reviews(targets)
                issues.extend(f"unresolved_review:{review['id']}" for review in outstanding)
            for artifact in data.get("artifacts", {}).values():
                try:
                    self.store.read_blob(artifact["sha256"])
                except (ControlError, OSError) as error:
                    issues.append(f"artifact_unavailable:{error}")
        return issues

    def _same_review_target(self, data):
        target = self.store.get(data["target_kind"], data["target_id"])
        return any(ref["kind"] == target["kind"] and ref["id"] == target["id"] and ref["digest"] == target["digest"]
                   for ref in data["dependencies"]["records"])

    def _review_relevant(self, data):
        if not self._snapshot_issues(data["dependencies"], {("skip_live_reviews",)}):
            return True
        # An editorial objection is not resolved just because its source note changed.
        return bool(data.get("findings")) and self._same_review_target(data)

    def _reviews_for_targets(self, targets, include_stale_objections=False):
        targets = set(targets)
        inherited = {}
        for kind, identity in targets:
            if kind == "draft":
                draft = self.store.get(kind, identity)
                for ref in draft["data"].get("inherited_reviews", []):
                    review = self.store.get("review", ref["id"])
                    if review["digest"] != ref["digest"] or review["data"]["project_id"] != draft["data"]["project_id"]:
                        raise ControlError("Inherited review identity or project mismatch")
                    inherited[review["id"]] = review
        for review in self.store.list("review"):
            data = review["data"]
            if (data["target_kind"], data["target_id"]) in targets and (
                self._review_relevant(data) or include_stale_objections and data["conclusion"] != "pass"):
                inherited[review["id"]] = review
        return list(inherited.values())

    def _outstanding_reviews(self, targets, include_stale_objections=False):
        reviews = self._reviews_for_targets(targets, include_stale_objections)
        resolved = set()
        for review in reviews:
            data = review["data"]
            if data["conclusion"] == "pass" and not data["issues"] and all(check["passed"] for check in data["checks"]):
                resolved.update(data.get("supersedes", []))
        return [review for review in reviews if review["id"] not in resolved and
                (review["data"]["conclusion"] != "pass" or review["data"]["issues"] or
                 not all(check["passed"] for check in review["data"]["checks"]))]

    def _decision_frontier(self, release_id):
        """Only objections and their explicit resolution affect an existing author decision."""
        release = self.store.get("release", release_id)
        draft = self.store.get("draft", release["data"]["draft_id"])
        targets = {("release", release_id), ("draft", draft["id"])}
        targets.update(("claim", claim_id) for claim_id in draft["data"]["claim_ids"])
        reviews = self._reviews_for_targets(targets)
        negatives = {review["id"] for review in reviews if review["data"]["conclusion"] != "pass" or review["data"]["issues"] or not all(check["passed"] for check in review["data"]["checks"])}
        return sorted(({"id": review["id"], "digest": review["digest"]} for review in reviews
                       if review["id"] in negatives or set(review["data"].get("supersedes", [])) & negatives), key=lambda item: item["id"])

    def _require_valid(self, snapshot):
        issues = self._snapshot_issues(snapshot)
        if issues:
            raise ControlError("Stale inputs: " + "; ".join(issues))

    def inspect(self, kind, record_id):
        record = self.store.get(kind, record_id)
        try:
            issues = self._record_issues(record)
        except (ControlError, OSError) as error:
            issues = [f"unavailable:{error}"]
        return {"kind": kind, "id": record_id, "digest": record["digest"], "valid": not issues,
                "status": "valid" if not issues else "stale", "issues": issues, "record": record}

    def impact(self, kind, record_id):
        self.store.get(kind, record_id)
        target = (kind, record_id)
        def depends(record, seen):
            key = (record["kind"], record["id"], record["digest"])
            if key in seen:
                return False
            seen.add(key)
            implicit = []
            if record["kind"] == "evidence":
                implicit.append(self._ref("source_version", record["data"]["source_version_id"]))
            if record["kind"] == "source_version":
                implicit.append(self._ref("source", record["data"]["source_id"]))
            for ref in implicit:
                if (ref["kind"], ref["id"]) == target or depends(self.store.get(ref["kind"], ref["id"], ref["revision"]), seen):
                    return True
            for field in ("dependencies", "inputs"):
                for ref in record["data"].get(field, {}).get("records", []):
                    if (ref["kind"], ref["id"]) == target:
                        return True
                    if depends(self.store.get(ref["kind"], ref["id"], ref["revision"]), seen):
                        return True
            return False
        results = []
        for dependent_kind in ("claim", "draft", "review", "release", "decision", "run", "delivery", "preview", "review_action"):
            for record in self.store.list(dependent_kind):
                if depends(record, set()):
                    results.append(self.inspect(dependent_kind, record["id"]))
        return {"target": {"kind": kind, "id": record_id}, "affected": results}

    def project_status(self, project_id):
        """Derived operational state; never mutate the project contract or dependency digest."""
        project = self.store.get("project", project_id)
        def records(kind):
            values = [r for r in self.store.list(kind) if r["data"].get("project_id") == project_id]
            return sorted(values, key=lambda r: (r["data"].get("created_at", r["data"].get("started_at", "")), r["id"]))
        def result(status, stage, next_action, basis):
            return {"project_id": project_id, "status": status, "stage": stage,
                    "next_action": next_action, "basis": basis, "derived": True,
                    "platform_verified": False, "project_digest": project["digest"]}
        deliveries = records("delivery")
        pending = [r for r in deliveries if r["data"]["state"] in {"submitted", "outcome_unknown"}]
        if pending:
            return result("awaiting_reconciliation", "delivery", "Check the external outcome and record a referenced reconciliation; do not resend.", [r["id"] for r in pending])
        if deliveries and deliveries[-1]["data"]["state"] == "published":
            return result("maintenance_reported_published", "maintenance", "Publication was caller-reported, not platform-verified; retain the reference, collect feedback and assess changes.", [deliveries[-1]["id"]])
        if deliveries and deliveries[-1]["data"]["state"] == "failed":
            return result("delivery_failed", "delivery", "Inspect the failure receipt and current package/decision before any newly authorized attempt.", [deliveries[-1]["id"]])
        runs = records("run")
        running = [r for r in runs if r["data"]["state"] == "running"]
        if running:
            return result("in_progress_or_interrupted", running[-1]["data"]["stage"], "Inspect the saved run and resume explicitly; no tool is automatically replayed.", [r["id"] for r in running])
        if runs and runs[-1]["data"]["state"] == "failed":
            return result("run_failed", runs[-1]["data"]["stage"], "Read the failure receipt, then resume within the attempt limit or revise the inputs.", [runs[-1]["id"]])
        releases = records("release")
        if releases:
            release = releases[-1]
            if not self.inspect("release", release["id"])["valid"]:
                return result("changes_need_review", "review", "Review changed inputs and prepare a new exact package after current checks.", [release["id"]])
            decisions = [d for d in records("decision") if d["data"]["release_id"] == release["id"]]
            if not decisions:
                return result("awaiting_author_decision", "author_decision", "The current package needs an explicit local author decision; reviews do not approve it.", [release["id"]])
            decision = decisions[-1]
            if decision["data"]["decision"] == "reject":
                return result("revision_requested", "draft", "Revise the rejected package according to the author's decision.", [release["id"], decision["id"]])
            if not self.inspect("decision", decision["id"])["valid"]:
                return result("changes_need_review", "review", "The prior decision is stale; review and decide on the current package.", [decision["id"]])
            return result("ready_for_authorized_delivery", "delivery", "A current local author attestation exists; perform only separately authorized external actions and retain receipts.", [release["id"], decision["id"]])
        drafts = records("draft")
        if drafts:
            draft = drafts[-1]
            if not self.inspect("draft", draft["id"])["valid"]:
                return result("changes_need_review", "draft", "Register the current draft and dependencies before reusing earlier reviews.", [draft["id"]])
            reviews = [r for r in records("review") if r["data"]["target_kind"] == "draft" and r["data"]["target_id"] == draft["id"]]
            outstanding = self._outstanding_reviews([("draft", draft["id"]), *[("claim", claim_id) for claim_id in draft["data"]["claim_ids"]]])
            if outstanding:
                return result("review_objections_open", "review", "Resolve the recorded objections with an explicit passing recheck that supersedes them.", [r["id"] for r in outstanding])
            if reviews:
                review = reviews[-1]
                data = review["data"]
                if self.inspect("review", review["id"])["valid"] and data["conclusion"] == "pass" and all(c["passed"] for c in data["checks"]) and not data["issues"]:
                    return result("ready_to_prepare", "adaptation", "Export and inspect the current draft, then prepare a package bound to this review.", [draft["id"], review["id"]])
            return result("awaiting_review", "review", "Record source/claim/paragraph checks and resolve outstanding issues for this exact draft.", [draft["id"]])
        claims = records("claim")
        if claims:
            stale = [r["id"] for r in claims if not self.inspect("claim", r["id"])["valid"]]
            if stale:
                return result("evidence_needs_recheck", "research", "Recheck withdrawn or changed evidence before drafting.", stale)
            return result("claim_candidates_ready", "draft", "Organize the candidate claims into a versioned draft; evidence coverage is not proof of truth.", [r["id"] for r in claims])
        return result("research_needed", "research", "Register scoped source versions and evidence, then form explicit claim candidates.", [project_id])

    def begin_run(self, project_id, stage, inputs, idempotency_key, tools=None, model=None):
        if not stage or not idempotency_key or inputs.get("project_id") != project_id:
            raise ControlError("Stage, idempotency key, and matching project snapshot are required")
        self._require_valid(inputs)
        project = self.store.get("project", project_id)
        tools = tools or []
        if not isinstance(tools, list) or not all(isinstance(tool, str) for tool in tools):
            raise ControlError("Run tools must be a list of names")
        tools = sorted(set(tools))
        if not set(tools) <= set(project["data"]["scope"]["tools"]):
            raise ControlError("Run tool outside project scope")
        identity = _hash({"project": project_id, "stage": stage, "inputs": inputs["digest"], "key": idempotency_key})
        run_id = "RUN-" + identity[:32]
        existing = next((run for run in self.store.list("run") if run["id"] == run_id), None)
        if existing:
            if existing["data"]["tools"] != tools or existing["data"].get("model") != model:
                raise ControlError("Idempotent run tool/model contract differs; use an explicit new key after reviewing scope")
            return existing
        related = [r for r in self.store.list("run") if r["data"]["project_id"] == project_id and r["data"]["stage"] == stage and r["data"]["inputs"]["digest"] == inputs["digest"]]
        attempts = sum(r["data"].get("attempts", 1) for r in related)
        if attempts >= project["data"]["max_attempts"]:
            raise ControlError("Project stage attempt limit reached")
        return self.store.create("run", {"project_id": project_id, "stage": stage, "inputs": inputs,
             "idempotency_key": idempotency_key, "state": "running", "attempts": 1, "tools": tools,
             "model": model, "cost": None, "cost_status": "unknown", "started_at": utc_now(), "receipts": []}, run_id)

    def _end_run(self, run_id, state, payload):
        record = self.store.get("run", run_id)
        if record["data"]["state"] != "running":
            raise ControlError("Only a running run can finish or fail")
        if state == "completed":
            self._require_valid(record["data"]["inputs"])
        receipt = self.store.create("receipt", {"type": "run_result", "run_id": run_id, "state": state,
                                                "at": utc_now(), **payload})
        elapsed = (datetime.fromisoformat(utc_now()) - datetime.fromisoformat(record["data"]["started_at"])).total_seconds()
        data = {**record["data"], "state": state, "ended_at": utc_now(), "elapsed_seconds": elapsed,
                "receipts": [*record["data"]["receipts"], receipt["id"]]}
        return self.store.update("run", run_id, data, record["digest"])

    def finish_run(self, run_id, outputs):
        return self._end_run(run_id, "completed", {"outputs": outputs})

    def fail_run(self, run_id, error):
        if not isinstance(error, str) or not error:
            raise ControlError("Failure reason required")
        return self._end_run(run_id, "failed", {"error": error})

    def resume_run(self, run_id):
        record = self.store.get("run", run_id)
        self._require_valid(record["data"]["inputs"])
        if record["data"]["state"] == "completed":
            return record
        attempts = record["data"]["attempts"]
        if record["data"]["state"] == "failed":
            project = self.store.get("project", record["data"]["project_id"])
            related = [r for r in self.store.list("run") if r["data"]["project_id"] == project["id"] and r["data"]["stage"] == record["data"]["stage"] and r["data"]["inputs"]["digest"] == record["data"]["inputs"]["digest"]]
            if sum(r["data"]["attempts"] for r in related) >= project["data"]["max_attempts"]:
                raise ControlError("Project stage attempt limit reached")
            attempts += 1
        receipt = self.store.create("receipt", {"type": "run_resume", "run_id": run_id, "at": utc_now(),
                                                "prior_state": record["data"]["state"], "executed_tools": False})
        data = {**record["data"], "state": "running", "attempts": attempts, "resumed_at": utc_now(),
                "receipts": [*record["data"]["receipts"], receipt["id"]]}
        return self.store.update("run", run_id, data, record["digest"])

    def register_claim(self, project_id, claim_id, claim_type, text, evidence_links, boundaries="", note_path=None, expected_digest=None):
        if claim_type not in CLAIM_TYPES or not isinstance(text, str) or not text.strip():
            raise ControlError("Valid claim_type and nonempty text are required")
        if not isinstance(evidence_links, list):
            raise ControlError("evidence_links must be a list")
        refs = []
        for link in evidence_links:
            if not isinstance(link, dict) or link.get("relation") not in RELATIONS or not link.get("evidence_id"):
                raise ControlError("Evidence links need evidence_id and explicit relation")
            refs.append({"kind": "evidence", "id": link["evidence_id"]})
        if claim_type != "personal_judgment" and not refs:
            raise ControlError("Source-based claims require evidence links")
        inputs = self.snapshot(project_id, [note_path] if note_path else [], refs)
        self._require_valid(inputs)
        data = {"project_id": project_id, "claim_type": claim_type, "text": text,
                "evidence_links": evidence_links, "boundaries": boundaries, "dependencies": inputs,
                "semantic_status": "candidate", "author_approved": False}
        if expected_digest is not None:
            if not self._owned_by(project_id, self.store.get("claim", claim_id)):
                raise ControlError("Cannot reassign a claim to another project")
            return self.store.update("claim", claim_id, data, expected_digest)
        return self.store.create("claim", data, claim_id)

    def register_draft(self, project_id, note_path, claim_ids, paragraphs, draft_id=None, parent_draft_id=None):
        if parent_draft_id is not None and (not isinstance(parent_draft_id, str) or not parent_draft_id.strip()):
            raise ControlError("Parent draft must be a nonempty ID or omitted for the latest draft")
        previous = sorted((r for r in self.store.list("draft") if r["data"]["project_id"] == project_id),
                          key=lambda r: (r["data"]["created_at"], r["id"]))
        if parent_draft_id is None and previous:
            parent_draft_id = previous[-1]["id"]
        inherited = []
        if parent_draft_id:
            parent = self.store.get("draft", parent_draft_id)
            if parent["data"]["project_id"] != project_id:
                raise ControlError("Parent draft belongs to another project")
            inherited = [self._ref("review", r["id"]) for r in
                         self._outstanding_reviews([("draft", parent_draft_id)], include_stale_objections=True)]
        path = self._path(project_id, note_path)
        value = path.read_bytes()
        text = value.decode("utf8")
        blocks = re.split(r"\n\s*\n", _body(text).strip())
        claim_ids = list(dict.fromkeys(claim_ids))
        refs = [{"kind": "claim", "id": claim_id} for claim_id in claim_ids]
        for ref in refs:
            if self.store.get(ref["kind"], ref["id"])["data"]["project_id"] != project_id:
                raise ControlError("Draft cannot borrow a claim from a different project")
        dependencies = self.snapshot(project_id, [note_path], refs)
        if dependencies["notes"][0]["sha256"] != digest(value):
            raise ControlError("Draft changed while registering; retry against current file")
        self._require_valid(dependencies)
        mappings, used = [], set()
        for entry in paragraphs:
            number = entry.get("paragraph")
            ids = entry.get("claim_ids", [])
            if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= len(blocks):
                raise ControlError("Paragraph index outside draft blocks")
            if not ids or not set(ids) <= set(claim_ids):
                raise ControlError("Paragraph mapping must use registered draft claims")
            used.update(ids)
            mappings.append({"paragraph": number, "claim_ids": ids, "text_sha256": digest(blocks[number - 1].encode())})
        if used != set(claim_ids):
            raise ControlError("Every draft claim must map to at least one paragraph")
        blob = self.store.blob(value)
        return self.store.create("draft", {"project_id": project_id, "note_path": note_path, "sha256": blob,
             "claim_ids": claim_ids, "paragraphs": mappings, "dependencies": dependencies,
             "parent_draft_id": parent_draft_id, "inherited_reviews": inherited,
             "status": "candidate", "created_at": utc_now()}, draft_id)

    def record_review(self, target_kind, target_id, checks, reviewer_type="ai", reviewer="unspecified", conclusion="needs_review", issues=None, supersedes=None,
                      findings=None, context_paths=None, attachments=None, review_id=None):
        if target_kind not in {"claim", "draft", "release"} or reviewer_type not in {"ai", "program", "human"}:
            raise ControlError("Unsupported review target or reviewer type")
        if conclusion not in REVIEW_CONCLUSIONS:
            raise ControlError("Review conclusion must be pass, needs_review, or fail")
        if not isinstance(checks, list) or not checks:
            raise ControlError("Review must record actual checks")
        for check in checks:
            if not isinstance(check, dict) or not check.get("name") or not isinstance(check.get("passed"), bool):
                raise ControlError("Each check needs name and boolean passed")
        target = self.store.get(target_kind, target_id)
        if findings is not None and not isinstance(findings, list):
            raise ControlError("Editorial findings must be a list")
        if attachments is not None and not isinstance(attachments, dict):
            raise ControlError("Review attachments must be a name-to-blob mapping")
        if context_paths is not None and (not isinstance(context_paths, list) or not all(isinstance(p, str) for p in context_paths)):
            raise ControlError("Review context paths must be a list of vault-relative paths")
        if findings:
            if target_kind != "draft" or not isinstance(findings, list):
                raise ControlError("Editorial findings require a draft target and a list")
            blocks = re.split(r"\n\s*\n", _body(self.store.read_blob(target["data"]["sha256"]).decode()).strip())
            ids = set()
            for finding in findings:
                if not isinstance(finding, dict) or not all(isinstance(finding.get(key), str) and finding[key].strip()
                    for key in ("id", "severity", "observation", "reason", "impact", "uncertainty")):
                    raise ControlError("Editorial finding needs identity and explicit review details")
                if finding["id"] in ids or not isinstance(finding.get("options"), list) or not finding["options"] or not all(isinstance(x, str) and x for x in finding["options"]):
                    raise ControlError("Editorial finding options/identity invalid")
                ids.add(finding["id"])
                if not isinstance(finding.get("mapped_anchors"), list) or not finding["mapped_anchors"]:
                    raise ControlError("Editorial finding requires mapped original anchors")
                for anchor in finding["mapped_anchors"]:
                    number = anchor.get("paragraph")
                    if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= len(blocks) or anchor.get("paragraph_sha256") != digest(blocks[number - 1].encode()):
                        raise ControlError("Editorial paragraph anchor does not match the draft")
                    if not isinstance(anchor.get("quote"), str) or not anchor["quote"] or anchor["quote"] not in blocks[number - 1]:
                        raise ControlError("Editorial quote does not match the draft")
                    if not all(isinstance(anchor.get(key), int) and not isinstance(anchor[key], bool) and anchor[key] > 0 for key in ("line_start", "line_end")):
                        raise ControlError("Editorial source lines required")
        for fingerprint in (attachments or {}).values():
            self.store.read_blob(fingerprint)
        dependencies = self.snapshot(target["data"]["project_id"], note_paths=context_paths,
                                     records=[{"kind": target_kind, "id": target_id}])
        # Rechecking a release with a known objection must be possible; ignore only live review objections,
        # while still validating its exact file, record, evidence and artifact dependencies.
        invalid = self._snapshot_issues(dependencies, {("skip_live_reviews",)})
        if invalid:
            raise ControlError("Stale review target: " + "; ".join(invalid))
        supersedes = list(dict.fromkeys(supersedes or []))
        if supersedes and (conclusion != "pass" or issues or not all(check["passed"] for check in checks)):
            raise ControlError("Only an explicit passing recheck can resolve earlier review issues")
        names = {check["name"] for check in checks}
        for earlier_id in supersedes:
            earlier = self.store.get("review", earlier_id)["data"]
            inherited = target_kind == "draft" and earlier_id in {ref["id"] for ref in target["data"].get("inherited_reviews", [])}
            same_target = earlier["target_kind"] == target_kind and earlier["target_id"] == target_id
            if earlier["project_id"] != target["data"]["project_id"] or not (same_target or inherited) or not {check["name"] for check in earlier["checks"]} <= names:
                raise ControlError("Recheck must cover the same target and all superseded check names")
            if not inherited and self._snapshot_issues(earlier["dependencies"], {("skip_live_reviews",)}) and not (
                earlier.get("findings") and self._same_review_target(earlier) and context_paths):
                raise ControlError("Cannot resolve a review of different stale inputs; review the new version explicitly")
        return self.store.create("review", {"project_id": target["data"]["project_id"], "target_kind": target_kind,
            "target_id": target_id, "checks": checks, "reviewer_type": reviewer_type, "reviewer": reviewer,
            "identity_provenance": "caller_declared_not_authenticated", "conclusion": conclusion, "issues": issues or [],
            "author_approved": False, "dependencies": dependencies, "supersedes": supersedes,
            "findings": findings or [], "attachments": attachments or {}, "created_at": utc_now()}, review_id)

    def record_preview(self, draft_id, artifact_dir, expected_selection=None):
        """Only a successful, still-current package changes the project selection."""
        from .bilibili_package import read_package
        draft = self.store.get("draft", draft_id)
        project_id = draft["data"]["project_id"]
        directory = self._path(project_id, artifact_dir, "write")
        values = read_package(directory, draft["data"]["sha256"])
        if values["article.md"].decode() != _body(self.store.read_blob(draft["data"]["sha256"]).decode()):
            raise ControlError("Preview body differs from registered draft")
        artifacts = {name: {"sha256": self.store.blob(raw), "bytes": len(raw)} for name, raw in values.items()}
        dependencies = self.snapshot(project_id, records=[{"kind": "draft", "id": draft_id}])
        identity = "PREVIEW-" + _hash({"draft": draft["digest"], "directory": artifact_dir, "artifacts": artifacts})[:32]
        record = next((r for r in self.store.list("preview") if r["id"] == identity), None)
        if record is None:
            record = self.store.create("preview", {"project_id": project_id, "draft_id": draft_id, "artifact_dir": artifact_dir,
                       "artifacts": artifacts, "dependencies": dependencies, "created_at": utc_now()}, identity)
        inspection = self.inspect("preview", identity)
        if not inspection["valid"]:
            return {"preview_id": identity, "selected": False, "inspection": inspection}
        current = next((r for r in self.store.list("selection") if r["id"] == project_id), None)
        if (current["digest"] if current else None) != expected_selection:
            raise ControlError("Preview selection changed concurrently; inspect before selecting again")
        selection = {"project_id": project_id, "preview_id": identity}
        if current:
            self.store.update("selection", project_id, selection, expected_selection)
        else:
            self.store.create("selection", selection, project_id)
        return {"preview_id": identity, "selected": True, "inspection": inspection}

    def prepare_release(self, project_id, draft_id, artifact_dir, review_ids, release_id=None):
        draft = self.store.get("draft", draft_id)
        if draft["data"]["project_id"] != project_id:
            raise ControlError("Draft belongs to another project")
        if not review_ids:
            raise ControlError("Release requires a current review of this exact draft")
        outstanding = self._outstanding_reviews([("draft", draft_id), *[("claim", claim_id) for claim_id in draft["data"]["claim_ids"]]])
        if outstanding:
            raise ControlError("Unresolved review objections: " + ", ".join(review["id"] for review in outstanding))
        refs = [{"kind": "draft", "id": draft_id}]
        draft_review = False
        for review_id in review_ids:
            review = self.store.get("review", review_id)
            data = review["data"]
            if data["project_id"] != project_id or data["conclusion"] != "pass" or not all(c["passed"] for c in data["checks"]) or data["issues"]:
                raise ControlError("Release review has failed checks, unresolved issues, or wrong project")
            draft_review |= data["target_kind"] == "draft" and data["target_id"] == draft_id
            refs.append({"kind": "review", "id": review_id})
        if not draft_review:
            raise ControlError("At least one review must inspect this exact draft")
        dependencies = self.snapshot(project_id, records=refs)
        self._require_valid(dependencies)
        directory = self._path(project_id, artifact_dir, "write")
        from .bilibili_package import read_package
        values = read_package(directory, draft["data"]["sha256"])
        if values["article.md"].decode("utf8") != _body(self.store.read_blob(draft["data"]["sha256"]).decode("utf8")):
            raise ControlError("Exported Markdown does not match the exact registered draft")
        artifacts = {name: {"sha256": self.store.blob(value), "bytes": len(value)} for name, value in values.items()}
        if any(safe_path(directory, name).read_bytes() != value for name, value in values.items()):
            raise ControlError("Export artifacts changed while preparing release")
        self._require_valid(dependencies)
        return self.store.create("release", {"project_id": project_id, "draft_id": draft_id,
             "draft_digest": draft["digest"], "artifacts": artifacts, "review_ids": review_ids,
             "dependencies": dependencies, "created_at": utc_now(), "status": "prepared",
             "format": "bilibili", "artifact_dir": artifact_dir,
             "platform_verified": False}, release_id)

    def record_decision(self, release_id, decision, author, *, input_stream=None, output_stream=None):
        if decision not in {"approve", "reject"} or not isinstance(author, str) or not author.strip():
            raise ControlError("Explicit author and approve/reject decision required")
        incoming = sys.stdin if input_stream is None else input_stream
        outgoing = sys.stdout if output_stream is None else output_stream
        if not incoming.isatty() or not outgoing.isatty():
            raise ControlError("Author decision requires a local interactive TTY; AI/review fields cannot approve")
        release = self.store.get("release", release_id)
        if decision == "approve" and not self.inspect("release", release_id)["valid"]:
            raise ControlError("Stale release cannot be approved")
        frontier = self._decision_frontier(release_id)
        phrase = f"{decision.upper()} {release_id} {release['digest']}"
        outgoing.write(f"Local author attestation only; no platform action.\nReview frontier: {_hash(frontier)} {canonical(frontier)}\nType exactly:\n{phrase}\n> ")
        outgoing.flush()
        if incoming.readline().rstrip("\r\n") != phrase:
            raise ControlError("Author confirmation did not match release digest")
        if self._decision_frontier(release_id) != frontier:
            raise ControlError("Review objections changed during author confirmation; inspect and confirm again")
        dependencies = self.snapshot(release["data"]["project_id"], records=[{"kind": "release", "id": release_id}])
        if decision == "approve":
            self._require_valid(dependencies)
        return self.store.create("decision", {"project_id": release["data"]["project_id"], "release_id": release_id,
             "release_digest": release["digest"], "decision": decision, "author": author,
             "provenance": "local_interactive_tty_attestation", "authenticated_identity": False,
             "review_frontier": frontier, "dependencies": dependencies, "created_at": utc_now()})

    def _approved_release(self, release_id):
        release = self.store.get("release", release_id)
        if not self.inspect("release", release_id)["valid"]:
            raise ControlError("Release or its dependencies changed")
        decisions = [d for d in self.store.list("decision") if d["data"]["release_id"] == release_id]
        decisions.sort(key=lambda d: d["data"]["created_at"])
        if not decisions or decisions[-1]["data"]["decision"] != "approve" or not self.inspect("decision", decisions[-1]["id"])["valid"]:
            raise ControlError("Exact release needs a current explicit author decision")
        return release, decisions[-1]

    def request_delivery(self, release_id, channel, idempotency_key):
        if not channel or not idempotency_key:
            raise ControlError("Delivery channel and idempotency key required")
        release, decision = self._approved_release(release_id)
        delivery_id = "DELIVERY-" + _hash({"release": release_id, "channel": channel, "key": idempotency_key})[:32]
        existing = self.store.list("delivery")
        for record in existing:
            if record["id"] == delivery_id:
                return record
            same_project_channel = record["data"]["project_id"] == release["data"]["project_id"] and record["data"]["channel"] == channel
            if same_project_channel and record["data"]["state"] in {"submitted", "outcome_unknown"}:
                raise ControlError("Existing delivery must be reconciled; never resend an unknown result")
            if same_project_channel and record["data"]["state"] == "published":
                previous = self.store.get("release", record["data"]["release_id"])
                if previous["data"]["artifacts"] == release["data"]["artifacts"]:
                    raise ControlError("Identical artifacts already have a published receipt; do not submit again")
        dependencies = self.snapshot(release["data"]["project_id"], records=[{"kind": "release", "id": release_id}, {"kind": "decision", "id": decision["id"]}])
        return self.store.create("delivery", {"project_id": release["data"]["project_id"], "release_id": release_id,
             "channel": channel, "idempotency_key": idempotency_key, "state": "submitted",
             "dependencies": dependencies, "receipts": [], "created_at": utc_now(),
             "tool_executed": False, "platform_verified": False, "provenance": "local_request_record_only"}, delivery_id)

    def _delivery_result(self, delivery_id, status, reference, details, reconcile):
        record = self.store.get("delivery", delivery_id)
        if status not in {"published", "failed", "outcome_unknown"} or not isinstance(reference, str) or not reference.strip():
            raise ControlError("Result needs a supported state and explicit evidence/reconciliation reference")
        current = record["data"]["state"]
        if current in {"published", "failed"}:
            raise ControlError("Terminal delivery receipt is immutable; record a new correction separately")
        if current == "outcome_unknown" and not reconcile:
            raise ControlError("Unknown outcome requires reconciliation, not another submission/result")
        if reconcile and current not in {"submitted", "outcome_unknown"}:
            raise ControlError("Nothing to reconcile")
        receipt = self.store.create("receipt", {"type": "delivery_reconciliation" if reconcile else "delivery_result",
             "delivery_id": delivery_id, "status": status, "reference": reference, "details": details,
             "at": utc_now(), "platform_verified": False, "provenance": "caller_reported_external_fact"})
        return self.store.update("delivery", delivery_id, {**record["data"], "state": status,
            "receipts": [*record["data"]["receipts"], receipt["id"]], "updated_at": utc_now()}, record["digest"])

    def record_delivery_result(self, delivery_id, status, reference, details=""):
        return self._delivery_result(delivery_id, status, reference, details, False)

    def reconcile_delivery(self, delivery_id, status, reference, details=""):
        return self._delivery_result(delivery_id, status, reference, details, True)
