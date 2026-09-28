# Change Local Workflow

When the user wants to change Trellis phases, next-action hints, whether to create tasks, whether to use sub-agents, or when to check/wrap up, edit `.trellis/workflow.md` first.

## Read These Files First

1. `.trellis/workflow.md`
2. Entry files for the current platform, such as skills/commands/prompts/workflows
3. The matching explicitly bound task and its canonical plan links, if this request belongs to that task

## Common Needs And Edit Points

| Need | Edit point |
| --- | --- |
| Change phase names or phase order | `Phase Index` and the corresponding Phase sections. |
| Change whether to create a task when there is no task | `[workflow-state:no_task]` state block. |
| Change the next step during planning | Phase 1 and `[workflow-state:planning]`. |
| Change whether an agent is required during in_progress | Phase 2 and `[workflow-state:in_progress]`. |
| Change wrap-up after completion | Phase 3 and `[workflow-state:completed]`. |
| Change which skill a user intent triggers | `Skill Routing` table. |

## Modification Steps

1. Find the relevant section in `.trellis/workflow.md`.
2. When changing rules, keep explicit trigger conditions and next actions.
3. If adding or renaming a skill/agent, synchronize the corresponding files in platform directories.
4. Workflow-state changes only need an edit to the `[workflow-state:STATUS]` block in `.trellis/workflow.md`. The hook is parser-only — it reads whatever you put in the block. Keep the opening and closing tags' STATUS strings identical (`[workflow-state:foo]…[/workflow-state:foo]`); mismatched STATUS pairs are silently dropped.
5. Make the AI reread `.trellis/workflow.md`; do not keep using rules from the old conversation.

## Example: Relax Task Creation Requirements

To change when task creation can be skipped, usually edit `[workflow-state:no_task]`:

```md
[workflow-state:no_task]
Analysis needs no task. Clear bounded edits may proceed without a new task unless project lifecycle rules require one. Complex work follows the canonical plan and prior authorization.
[/workflow-state:no_task]
```

If the formal Phase 1 flow also needs to change, synchronize the Phase 1 section.

## Example: One Platform Does Not Use Sub-Agents

If the user wants only one platform to avoid sub-agents, first confirm whether that platform has a separate group in the workflow. Then change Phase 2 routing for that platform group instead of deleting all `trellis-implement` / `trellis-check` instructions across platforms.

## `/trellis:continue` Route Table

`/trellis:continue` resumes a task by deciding which phase step to load next. The decision combines `task.json.status` with the presence of artifacts inside the task directory. Keep the command, canonical planning links, current evidence and workflow.md routing coherent; do not infer readiness from filenames alone.

| `status` | Artifact state | Resume at |
| --- | --- | --- |
| `planning` | `prd.md` missing | Phase 1.1 (load `trellis-brainstorm`) |
| `planning` | lightweight plan sufficient | start only when implementation is authorized; reuse prior approval |
| `planning` | canonical design or execution decisions incomplete | complete the missing content; read linked plans instead of duplicating them |
| `planning` | canonical plan sufficient and reviewed | start within existing implementation authorization; ask only for a material scope/risk change |
| `in_progress` | authorized implementation incomplete | Phase 2.1, main-session by default; inspect current evidence |
| `in_progress` | implementation done, no `trellis-check` run | Phase 2.2 (`trellis-check`) |
| `in_progress` | check evidence current | 3.3 only for durable deltas → 3.4 only authorized delivery → report |
| `completed` | task is still in active tree | report actual evidence; archive only with explicit target authorization and complete acceptance |

When you add a custom status (e.g. `in-review`), add a `[workflow-state:in-review]` block in `.trellis/workflow.md` for the per-turn breadcrumb AND extend this route table — usually by editing the `/trellis:continue` command file (`.{platform}/commands/trellis/continue.md` or equivalent) to add a row that decides where to resume from. Without the route entry, `/trellis:continue` will fall through to a default branch and the user will not land on the step you intended.

## Notes

`.trellis/workflow.md` is the local project workflow, not an immutable template. The user can adapt it to team habits. After editing it, platform entry files may still contain old descriptions, so inspect them too.
