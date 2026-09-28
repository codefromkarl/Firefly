#!/usr/bin/env python3
"""Explicit local knowledge-production commands. No daemon or automatic publishing."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from creator_system.store import Store, ControlError, digest, safe_path
from creator_system import sources
from creator_system.workflow import Workflow
from creator_system.workbench import track_legacy_notes, propose_change, candidate_status, system_status, write_dashboard
from creator_system.backup import backup_vault, verify_backup, restore_backup
from creator_system.runner import run_tool


def read_json(filename):
    return json.loads(Path(filename).read_text(encoding="utf8"))


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--vault", type=Path, help="Existing private Obsidian vault; optional for restore and backup-verify")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Index existing notes without changing them; create system dashboard")
    commands.add_parser("status", help="Current facts and revision validity")
    commands.add_parser("audit", help="Check database history and referenced blobs without changing records")
    commands.add_parser("dashboard", help="Explicitly refresh the generated system homepage")
    add = commands.add_parser("source-add", help="Register an explicit source file or supplied web snapshot")
    add.add_argument("--path", required=True, type=Path)
    add.add_argument("--id", required=True)
    for name in ["title", "work-id", "url", "legacy-note"]:
        add.add_argument(f"--{name}")
    add.add_argument("--capture-scope", choices=["full", "excerpt", "unknown"], default="full")
    add.add_argument("--ocr", action="store_true")
    for name in ["source-units", "source-status"]:
        commands.add_parser(name).add_argument("--version", required=True)
    read = commands.add_parser("source-read")
    read.add_argument("--version", required=True)
    read.add_argument("--locator", required=True, help="Exact JSON locator returned by source-units/search")
    read.add_argument("--context", type=int, default=1)
    search = commands.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--version")
    search.add_argument("--topk", type=int, default=5)
    evidence = commands.add_parser("evidence-add")
    evidence.add_argument("--version", required=True)
    evidence.add_argument("--locator", required=True)
    evidence.add_argument("--quote")
    commands.add_parser("evidence-read").add_argument("--id", required=True)
    recover = commands.add_parser("source-recover", help="Recover verified snapshot to a new private file; never reactivate an old/withdrawn source")
    recover.add_argument("--version", required=True)
    recover.add_argument("--to", help="New vault-relative destination; defaults to private recovered-source directory")
    web = commands.add_parser("web-check", help="Explicit public-URL HEAD probe; does not verify article content")
    web.add_argument("--source", required=True)
    withdraw = commands.add_parser("source-withdraw")
    withdraw.add_argument("--id", required=True)
    withdraw.add_argument("--reason", required=True)
    project = commands.add_parser("project-create")
    project.add_argument("--id", required=True)
    project.add_argument("--goal", required=True)
    project.add_argument("--scope", help="JSON with read_paths/write_paths/tools/network")
    project.add_argument("--max-attempts", type=int, default=3)
    begin = commands.add_parser("run-start")
    begin.add_argument("--project", required=True)
    begin.add_argument("--stage", required=True)
    begin.add_argument("--key", required=True)
    begin.add_argument("--notes", nargs="*", default=[])
    begin.add_argument("--records", help="JSON list of {kind,id} input records")
    begin.add_argument("--tools", nargs="*", default=[])
    begin.add_argument("--model")
    tool = commands.add_parser("run-tool", help="Execute an allowed read tool and preserve real input/output receipts")
    tool.add_argument("--project", required=True)
    tool.add_argument("--tool", choices=["search", "source-read", "evidence-read"], required=True)
    tool.add_argument("--arguments", required=True, help="JSON tool argument file")
    tool.add_argument("--key", required=True)
    finish = commands.add_parser("run-complete")
    finish.add_argument("--id", required=True)
    finish.add_argument("--outputs", required=True, help="JSON stage output summary")
    fail = commands.add_parser("run-fail")
    fail.add_argument("--id", required=True)
    fail.add_argument("--error", required=True)
    commands.add_parser("run-resume").add_argument("--id", required=True)
    for name in ["claim-register", "draft-register", "review", "release-prepare"]:
        commands.add_parser(name).add_argument("--spec", required=True, help="Explicit JSON spec; see workflow-controls.md")
    for name in ["inspect", "impact"]:
        check = commands.add_parser(name)
        check.add_argument("--kind", required=True)
        check.add_argument("--id", required=True)
    preview = commands.add_parser("preview", help="Export captured draft as Bilibili package; no approval or publishing")
    preview.add_argument("--draft", required=True)
    preview.add_argument("--assets", help="Vault-relative Bilibili image manifest within project read scope")
    preview.add_argument("--output", help="New vault-relative version directory within project write scope")
    editorial = commands.add_parser("review-import", help="Import scoped semantic review candidates for an exact draft")
    editorial.add_argument("--draft", required=True)
    for name in ("packet", "analysis", "review"):
        editorial.add_argument(f"--{name}", required=True, help="Vault-relative input path")
    impact = commands.add_parser("draft-impact", help="Compare an edited note to a reviewed draft; no changes or approvals")
    impact.add_argument("--draft", required=True)
    impact.add_argument("--input", required=True, help="Vault-relative edited note")
    impact.add_argument("--review", required=True, help="Imported semantic review ID")
    action = commands.add_parser("review-action", help="Record revise/retain/defer intent; does not resolve a review")
    action.add_argument("--draft", required=True)
    item = action.add_mutually_exclusive_group(required=True)
    item.add_argument("--review", help="Exact unresolved review ID")
    item.add_argument("--finding", help="Unique visible finding ID on this draft, e.g. IR-F01")
    action.add_argument("--action", choices=["revise", "retain", "defer"], required=True)
    action.add_argument("--reason", required=True)
    action.add_argument("--actor", required=True, help="Declared person/assistant; not author approval")
    action.add_argument("--candidate", help="Optional vault-relative revised candidate; original is never overwritten")
    decision = commands.add_parser("author-decision", help="Interactive local author decision; no publication")
    decision.add_argument("--release", required=True)
    decision.add_argument("--decision", choices=["approve", "reject"], required=True)
    decision.add_argument("--author", required=True)
    request = commands.add_parser("delivery-request", help="Record an intended external action, does not send it")
    request.add_argument("--release", required=True)
    request.add_argument("--channel", required=True)
    request.add_argument("--key", required=True)
    for name in ["delivery-result", "delivery-reconcile"]:
        result = commands.add_parser(name)
        result.add_argument("--id", required=True)
        result.add_argument("--status", choices=["published", "failed", "outcome_unknown"], required=True)
        result.add_argument("--reference", required=True)
        result.add_argument("--details", default="")
    candidate = commands.add_parser("propose")
    candidate.add_argument("--note", required=True)
    candidate.add_argument("--candidate", required=True, type=Path)
    candidate.add_argument("--expected-hash", required=True)
    commands.add_parser("candidate-status").add_argument("--id", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("--to", required=True, type=Path)
    backup.add_argument("--purpose", choices=["manual_backup", "local_recovery_drill"], default="manual_backup")
    commands.add_parser("backup-verify").add_argument("--file", required=True, type=Path)
    restore = commands.add_parser("restore")
    restore.add_argument("--file", required=True, type=Path)
    restore.add_argument("--to", required=True, type=Path)
    return root


def execute(store, args):
    workflow = Workflow(store)
    command = args.command
    if command == "init":
        indexed = track_legacy_notes(store)
        return {"index": indexed, "dashboard": write_dashboard(store)["path"]}
    if command == "status": return system_status(store)
    if command == "audit":
        from creator_system.integrity import audit_database
        return {"integrity": audit_database(store.db, store.read_blob), "meaning": "Structural integrity only; not semantic review or author approval."}
    if command == "dashboard": return write_dashboard(store)
    if command == "source-add":
        return sources.register_source(store, args.path, args.id, title=args.title, work_id=args.work_id,
                                       url=args.url, capture_scope=args.capture_scope, ocr=args.ocr, legacy_note=args.legacy_note)
    if command == "source-units": return sources.list_units(store, args.version)
    if command == "source-status": return sources.source_status(store, args.version)
    if command == "source-read": return sources.read_source(store, args.version, args.locator, context=args.context)
    if command == "search": return sources.search(store, args.query, source_version_id=args.version, topk=args.topk)
    if command == "evidence-add": return sources.create_evidence(store, args.version, args.locator, quote=args.quote)
    if command == "evidence-read": return sources.replay_evidence(store, args.id)
    if command == "source-recover":
        from creator_system.recovery import recover_source
        return recover_source(store, args.version, args.to)
    if command == "web-check":
        from creator_system.web_access import check_web_source
        return check_web_source(store, args.source)
    if command == "source-withdraw": return sources.withdraw_source(store, args.id, args.reason)
    if command == "project-create":
        scope = read_json(args.scope) if args.scope else {"read_paths": ["."], "write_paths": ["40 内容项目", ".creator-system/exports"], "tools": [], "network": False}
        return workflow.create_project(args.id, args.goal, scope, args.max_attempts)
    if command == "run-start":
        inputs = workflow.snapshot(args.project, args.notes, read_json(args.records) if args.records else [])
        return workflow.begin_run(args.project, args.stage, inputs, args.key, args.tools, args.model)
    if command == "run-tool": return run_tool(store, args.project, args.tool, read_json(args.arguments), args.key)
    if command == "run-complete": return workflow.finish_run(args.id, read_json(args.outputs))
    if command == "run-fail": return workflow.fail_run(args.id, args.error)
    if command == "run-resume": return workflow.resume_run(args.id)
    spec_actions = {"claim-register": workflow.register_claim, "draft-register": workflow.register_draft,
                    "review": workflow.record_review, "release-prepare": workflow.prepare_release}
    if command in spec_actions:
        spec = read_json(args.spec)
        if not isinstance(spec, dict): raise ControlError("Expected a JSON object spec")
        return spec_actions[command](**spec)
    if command == "inspect": return workflow.inspect(args.kind, args.id)
    if command == "impact": return workflow.impact(args.kind, args.id)
    if command == "review-import":
        from creator_system.editorial import import_review
        return import_review(store, args.draft, args.packet, args.analysis, args.review)
    if command == "draft-impact":
        from creator_system.editorial import draft_impact
        return draft_impact(store, args.draft, args.input, args.review)
    if command == "review-action":
        from creator_system.editorial import record_action
        result = record_action(store, args.draft, args.action, args.reason, args.actor,
                               review_id=args.review, finding_id=args.finding, candidate_path=args.candidate)
        try:
            dashboard = {"path": write_dashboard(store)["path"]}
        except (ControlError, OSError) as error:
            dashboard = {"warning": str(error), "preserved_manual_edits": True}
        return {"action": result, "dashboard": dashboard, "author_approved": False}
    if command == "preview":
        draft = store.get("draft", args.draft)
        previous_selection = next((r for r in store.list("selection") if r["id"] == draft["data"]["project_id"]), None)
        expected_selection = previous_selection["digest"] if previous_selection else None
        assets, asset_identity = None, "none"
        if args.assets:
            assets = workflow._path(draft["data"]["project_id"], args.assets)
            manifest_raw = assets.read_bytes()
            manifest = json.loads(manifest_raw)
            fingerprints = [digest(manifest_raw)]
            for item in manifest["images"]:
                image = safe_path(assets.parent, item["path"])
                workflow._path(draft["data"]["project_id"], image.relative_to(store.vault).as_posix())
                fingerprints.append(digest(image.read_bytes()))
            asset_identity = digest(json.dumps(fingerprints).encode())[:16]
        raw = store.read_blob(draft["data"]["sha256"])
        target = safe_path(store.root, f"preview-inputs/{draft['data']['sha256']}.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != raw:
                raise ControlError("Preview snapshot was modified")
        else:
            with target.open("xb") as stream:
                stream.write(raw)
        relative = args.output or f".creator-system/exports/{args.draft}-{draft['digest'][:12]}-bilibili-{asset_identity}"
        output = safe_path(store.vault, relative)
        workflow._path(draft["data"]["project_id"], relative, "write")
        exporter = Path(__file__).resolve().parent / "creator_system/bilibili-render.mjs"
        export_args = ["node", str(exporter), "--input", str(target), "--output", str(output)]
        if assets: export_args += ["--assets", str(assets)]
        result = subprocess.run(export_args,
                                capture_output=True, text=True, timeout=90, check=False)
        if result.returncode:
            raise ControlError(result.stderr[-2000:] or "Preview export failed")
        if assets and (assets.read_bytes() != manifest_raw or
                       any(digest(safe_path(assets.parent, item["path"]).read_bytes()) != fingerprint
                           for item, fingerprint in zip(manifest["images"], fingerprints[1:]))):
            raise ControlError("Image inputs changed during preview; preserve output and use a stable new version")
        selection = workflow.record_preview(args.draft, relative, expected_selection)
        try:
            dashboard = {"path": write_dashboard(store)["path"]}
        except (ControlError, OSError) as error:
            dashboard = {"warning": str(error), "preserved_manual_edits": True}
        return {"artifacts": relative, "preview": json.loads(result.stdout), "inspection": workflow.inspect("draft", args.draft),
                "selection": selection, "dashboard": dashboard, "format": "bilibili", "publication": "not_published"}
    if command == "author-decision": return workflow.record_decision(args.release, args.decision, args.author)
    if command == "delivery-request": return workflow.request_delivery(args.release, args.channel, args.key)
    if command == "delivery-result": return workflow.record_delivery_result(args.id, args.status, args.reference, args.details)
    if command == "delivery-reconcile": return workflow.reconcile_delivery(args.id, args.status, args.reference, args.details)
    if command == "propose": return propose_change(store, args.note, args.candidate.read_text(), args.expected_hash)
    if command == "candidate-status": return candidate_status(store, args.id)
    if command == "backup": return backup_vault(store, args.to, purpose=args.purpose)
    if command == "backup-verify": return verify_backup(args.file)
    if command == "restore":
        report = restore_backup(args.file, args.to)
        store.event("restore_verified", {"backup_sha256": report["archive_sha256"], **report})
        for backup in store.list("backup"):
            if backup["data"]["sha256"] == report["archive_sha256"]:
                store.update("backup", backup["id"], {**backup["data"], "restore_tested": True}, backup["digest"])
        return report
    raise ControlError("Unknown command")


def main():
    args = parser().parse_args()
    if args.command in {"restore", "backup-verify"}:
        report = restore_backup(args.file, args.to) if args.command == "restore" else verify_backup(args.file)
        # Disaster recovery does not require a surviving original vault.
        if args.command == "restore" and args.vault and (args.vault.expanduser() / ".creator-system/state.sqlite3").is_file():
            origin = None
            try:
                origin = Store(args.vault)
                event = origin.event("restore_verified", {"backup_sha256": report["archive_sha256"], **report})
                for backup in origin.list("backup"):
                    if backup["data"]["sha256"] == report["archive_sha256"]:
                        origin.update("backup", backup["id"], {**backup["data"], "restore_tested": True,
                                      "restore_receipt": event["id"], "restore_destination": report["destination"]}, backup["digest"])
            except Exception as error:
                report["origin_receipt_warning"] = f"Recovery succeeded; original-store receipt unavailable: {type(error).__name__}"
            finally:
                if origin is not None: origin.close()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    if args.vault is None or not args.vault.expanduser().is_dir():
        raise ControlError("Vault does not exist; create or open it before initializing controls")
    store = Store(args.vault)
    try:
        result = execute(store, args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    try:
        main()
    except (ControlError, OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"error": str(error), "operation_completed": False}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
