---
name: trellis-continue
description: "Resume the matching task from canonical artifacts and current evidence while preserving unrelated task state and existing authorization."
---

# Continue Work

Check whether this request belongs to the explicitly bound task. Unrelated analysis leaves it unchanged. If no matching task exists, use workflow request triage rather than creating one for every conversation.

Read current task source/status and the compact Phase Index only as needed:

```bash
python3 .trellis/scripts/task.py current --source
python3 .trellis/scripts/get_context.py --mode phase
```

Read canonical planning targets through artifact links. Route by evidence:

- Planning incomplete: resolve only missing consequential decisions (1.1).
- Planning sufficient and implementation authorized: activate if necessary (1.4), then implement (2.1). Prior approval remains valid.
- Implementation incomplete: continue 2.1; inline mode works directly.
- Implementation complete but evidence missing/stale: check 2.2.
- Checks current: update a durable spec delta only if needed (3.3), perform only authorized delivery (3.4), report (3.5).
- Completed metadata: verify actual acceptance; do not automatically archive.

Use `get_context.py --mode phase --step <X.Y>` for detail. Optional pointer artifacts or skipped inline manifests are valid. Do not repeat satisfied steps, task-creation/start questions or passing checks just because this is a new turn. Keep each project's task/validation state local.
