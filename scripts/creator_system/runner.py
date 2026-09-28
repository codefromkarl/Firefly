"""Execute a small allowlist of read-only tools with real run/result receipts."""
from . import sources
from .store import ControlError, canonical, digest
from .workflow import Workflow


def run_tool(store, project_id, tool, arguments, idempotency_key):
    workflow = Workflow(store)
    if tool not in {"search", "source-read", "evidence-read"}:
        raise ControlError("Only search/source-read/evidence-read may be executed by this local runner")
    if not isinstance(arguments, dict):
        raise ControlError("Tool arguments must be an object")
    refs = []
    if tool == "evidence-read":
        refs.append({"kind": "evidence", "id": arguments["evidence_id"]})
    elif arguments.get("source_version_id"):
        refs.append({"kind": "source_version", "id": arguments["source_version_id"]})
    else:
        refs.extend({"kind": "source_version", "id": row["data"]["active_version_id"]}
                    for row in store.list("source") if not row["data"].get("withdrawn"))
    inputs = workflow.snapshot(project_id, records=refs)
    inputs["tool_arguments"] = arguments
    inputs["tool"] = tool
    inputs["digest"] = digest(canonical({k: v for k, v in inputs.items() if k != "digest"}).encode())
    run = workflow.begin_run(project_id, "research", inputs, idempotency_key, tools=[tool])
    if run["data"]["state"] == "completed":
        receipt = store.get("receipt", run["data"]["receipts"][-1])
        return {"run": run, "result": receipt["data"]["outputs"], "reused": True}
    if run["data"]["state"] == "failed":
        run = workflow.resume_run(run["id"])
    try:
        if tool == "search":
            output = sources.search(store, **arguments)
        elif tool == "source-read":
            output = sources.read_source(store, **arguments)
        else:
            if set(arguments) != {"evidence_id"}:
                raise ControlError("evidence-read accepts only evidence_id")
            output = sources.replay_evidence(store, arguments["evidence_id"])
        result = workflow.finish_run(run["id"], output)
        return {"run": result, "result": output, "reused": False}
    except Exception as error:
        current = store.get("run", run["id"])
        if current["data"]["state"] == "running":
            workflow.fail_run(run["id"], str(error))
        raise
