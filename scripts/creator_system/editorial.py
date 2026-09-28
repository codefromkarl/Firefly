"""Bridge explicitly supplied editorial candidates into the existing review workflow."""
import json
import re
from pathlib import Path

from .semantic import prepare_document, pack_fingerprint, validate_review, compare_documents
from .store import ControlError, canonical, digest, utc_now
from .workflow import Workflow, _body


def map_anchors(text, pack, finding):
    paragraphs = re.split(r"\n\s*\n", _body(text).strip())
    blocks = {block["id"]: block for block in pack["blocks"]}
    result = []
    for anchor in finding["anchors"]:
        block = blocks[anchor["block_id"]]
        matches = [i for i, paragraph in enumerate(paragraphs, 1) if block["text"].strip() in paragraph]
        if block.get("ambiguous") or len(matches) != 1:
            raise ControlError("Ambiguous editorial anchor; map repeated text explicitly before import")
        number = matches[0]
        result.append({**anchor, "paragraph": number, "paragraph_sha256": digest(paragraphs[number - 1].encode()),
                       "line_start": block["line_start"], "line_end": block["line_end"], "section": block["section"]})
    return result


def import_review(store, draft_id, packet_path, analysis_path, review_path):
    flow = Workflow(store)
    draft = store.get("draft", draft_id)
    project = draft["data"]["project_id"]
    paths = [packet_path, analysis_path, review_path]
    raw = [flow._path(project, path).read_bytes() for path in paths]
    pack, analysis, review = [json.loads(value) for value in raw]
    document = flow._path(project, draft["data"]["note_path"])
    if Path(pack["document"]["path"]) != document or pack["document"]["sha256"] != draft["data"]["sha256"]:
        raise ControlError("Editorial packet does not match this registered draft")
    sources = []
    for source in pack.get("sources", []):
        try:
            relative = Path(source["path"]).relative_to(store.vault).as_posix()
        except ValueError as error:
            raise ControlError("Editorial source outside vault") from error
        sources.append(flow._path(project, relative))
        paths.append(relative)
    if pack_fingerprint(prepare_document(document, sources)) != pack_fingerprint(pack):
        raise ControlError("Editorial packet/source content is stale or altered")
    validation = validate_review(pack, analysis, review)
    if not validation["valid"]:
        raise ControlError("Invalid editorial review: " + "; ".join(validation["errors"]))
    text = store.read_blob(draft["data"]["sha256"]).decode()
    findings = [{**finding, "mapped_anchors": map_anchors(text, pack, finding)} for finding in review["findings"]]
    # Validate every finding and all inputs before creating any reviews.
    snapshot = flow.snapshot(project, paths, [{"kind": "draft", "id": draft_id}])
    flow._require_valid(snapshot)
    if any(flow._path(project, path).read_bytes() != value for path, value in zip(paths[:3], raw)):
        raise ControlError("Editorial inputs changed during import")
    attachments = {key: store.blob(value) for key, value in zip(("packet", "analysis", "review"), raw)}
    reviews = []
    for finding in findings:
        identity = "REVIEW-SEM-" + digest(canonical({"draft": draft["digest"], "inputs": attachments, "finding": finding["id"]}).encode())[:32]
        existing = next((r for r in store.list("review") if r["id"] == identity), None)
        flow._require_valid(snapshot)
        if existing is None:
            existing = flow.record_review("draft", draft_id,
                [{"name": "语义意见 " + finding["id"], "passed": False, "details": finding["observation"]}],
                reviewer_type=review["reviewer"]["kind"], reviewer=review["reviewer"]["name"],
                conclusion="needs_review", issues=[finding["observation"]], findings=[finding],
                context_paths=paths, attachments=attachments, review_id=identity)
        reviews.append(existing["id"])
    return {"review_ids": reviews, "findings": len(findings), "author_approved": False,
            "meaning": "Imported candidates require explicit recheck; source notes are not primary-source verification."}


def draft_impact(store, draft_id, note_path, review_id):
    flow = Workflow(store)
    draft = store.get("draft", draft_id)
    review = store.get("review", review_id)
    if review["data"]["target_kind"] != "draft" or review["data"]["target_id"] != draft_id:
        raise ControlError("Impact review must belong to this exact draft")
    attachments = review["data"].get("attachments", {})
    if not {"packet", "analysis"} <= attachments.keys():
        raise ControlError("Impact requires an imported editorial review")
    pack, analysis = [json.loads(store.read_blob(attachments[key])) for key in ("packet", "analysis")]
    project = draft["data"]["project_id"]
    # Historical packets keep their original absolute paths; resolve note dependencies
    # against this vault after a verified restore to a new directory.
    original_root = Path(pack["document"]["path"]).parents[len(Path(draft["data"]["note_path"]).parts) - 1]
    sources = [flow._path(project, Path(source["path"]).relative_to(original_root).as_posix()) for source in pack.get("sources", [])]
    new = prepare_document(flow._path(project, note_path), sources)
    result = compare_documents(pack, new, analysis)
    old_blocks = re.split(r"\n\s*\n", _body(store.read_blob(draft["data"]["sha256"]).decode()).strip())
    new_blocks = re.split(r"\n\s*\n", _body(flow._path(project, note_path).read_text()).strip())
    suggestions, unresolved = [], []
    for mapping in draft["data"]["paragraphs"]:
        value = old_blocks[mapping["paragraph"] - 1]
        matches = [i for i, block in enumerate(new_blocks, 1) if block == value]
        if len(matches) == 1 and old_blocks.count(value) == 1:
            suggestions.append({"old_paragraph": mapping["paragraph"], "paragraph": matches[0], "claim_ids": mapping["claim_ids"], "text_sha256": digest(value.encode())})
        else:
            unresolved.append(mapping["paragraph"])
    return {**result, "claim_mapping_candidates": suggestions, "unresolved_claim_paragraphs": unresolved,
            "review_reused": False, "author_approved": False}


def record_action(store, draft_id, action, reason, actor, *, review_id=None, finding_id=None, candidate_path=None):
    """Record editorial intent against this revision; never resolves or approves it."""
    if action not in {"revise", "retain", "defer"} or not all(isinstance(v, str) and v.strip() for v in (reason, actor)):
        raise ControlError("Action needs revise/retain/defer, an explicit reason and a declared actor")
    if bool(review_id) == bool(finding_id):
        raise ControlError("Provide exactly one review ID or finding ID")
    if candidate_path and action != "revise":
        raise ControlError("A candidate manuscript belongs to a revise action")
    flow = Workflow(store)
    draft = store.get("draft", draft_id)
    project = draft["data"]["project_id"]
    outstanding = flow._outstanding_reviews([("draft", draft_id)])
    matching = [review for review in outstanding if review["id"] == review_id or
                finding_id and any(finding.get("id") == finding_id for finding in review["data"].get("findings", []))]
    if len(matching) != 1:
        raise ControlError("Finding/review must identify one unresolved item on this draft; use its exact review ID if ambiguous")
    review = matching[0]
    notes = [note["path"] for note in review["data"]["dependencies"].get("notes", [])]
    candidate = None
    if candidate_path:
        candidate = flow._path(project, candidate_path).read_bytes()
        if not candidate.strip():
            raise ControlError("Candidate manuscript is empty")
        notes.append(candidate_path)
    dependencies = flow.snapshot(project, notes, [{"kind": "draft", "id": draft_id}])
    flow._require_valid(dependencies)
    if candidate is not None and not any(note["path"] == candidate_path and note["sha256"] == digest(candidate) for note in dependencies["notes"]):
        raise ControlError("Candidate changed while recording action")
    data = {"project_id": project, "draft_id": draft_id, "review_ref": flow._ref("review", review["id"]),
            "action": action, "reason": reason.strip(), "actor": actor.strip(), "candidate_path": candidate_path,
            "candidate_blob": store.blob(candidate) if candidate is not None else None,
            "dependencies": dependencies, "identity_provenance": "caller_declared_not_authenticated",
            "author_approved": False, "resolves_review": False, "status": "awaiting_recheck"}
    previous = sorted((row for row in store.list("review_action") if row["data"]["draft_id"] == draft_id and
                       row["data"]["review_ref"]["id"] == review["id"]), key=lambda row: (row["data"]["created_at"], row["id"]))
    if previous and {key: value for key, value in previous[-1]["data"].items() if key not in {"created_at", "previous_action_id"}} == data:
        return previous[-1]
    data["previous_action_id"] = previous[-1]["id"] if previous else None
    identity = "ACTION-" + digest(canonical(data).encode())[:32]
    existing = next((row for row in store.list("review_action") if row["id"] == identity), None)
    if existing:
        return existing
    flow._require_valid(dependencies)
    return store.create("review_action", {**data, "created_at": utc_now()}, identity)
