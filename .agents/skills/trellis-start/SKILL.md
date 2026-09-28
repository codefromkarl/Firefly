---
name: trellis-start
description: "Load relevant project context and route the current request without unnecessary task creation or approval pauses."
---

# Start Session

Classify the current request before acting on any active-task hint. Analysis needs no task or finish ceremony. Clear bounded edits may proceed with applicable rules and checks. Complex work follows the project's canonical plan and lifecycle rules.

1. Locate the current repository; read its AGENTS.md and relevant rules. If Trellis is absent, follow the existing workflow; do not initialize it unless requested.
2. When Trellis is relevant, inspect `python3 .trellis/scripts/task.py current --source` and git status. Preserve unrelated task bindings and WIP. Do not adopt a repository-visible task without a matching session/request.
3. Read the compact Phase Index with `python3 .trellis/scripts/get_context.py --mode phase`; load a specific step only when needed. Read relevant spec indexes, not the whole spec tree. Reuse unchanged context already read.
4. Route by user intent and evidence, not task status alone: unresolved planning → brainstorm; authorized edits → before-dev; changed behavior → check; resume → continue.

Use project-local skills before same-name global fallbacks. Existing approval to execute a plan covers necessary local preparation and checks. Ask only consequential unresolved questions; commit, external actions and archive still need authorization covering each operation.
