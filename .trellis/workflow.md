# Development Workflow

Personal workflow revision: 2026-09-07. Project architecture, business invariants, lifecycle ownership, validation gates and release permissions remain authoritative in the project's own rules.

## Working agreements

- First classify the current request; an active-task hint does not make an unrelated question part of that task. Preserve unrelated task bindings and work.
- Reuse authorization already given in this conversation. A request to execute an agreed plan authorizes its necessary local preparation, edits and checks. Ask again only for a material scope change or an operation not yet authorized.
- Commit, push, PR publication, merge, deployment, business-database migration, provider actions, archive and worktree removal require authorization covering that operation. One explicit instruction may authorize several named operations; do not ask once per operation when already covered.
- Preserve shared dirty files. Never reset, stash, clean or stage unrelated work. Keep task state, evidence, rules and commands in their owning project.
- If this project has no Trellis, use its existing workflow. Do not initialize Trellis or install hooks unless requested.
- Use the project-local skill for a given name when present; global skills are a fallback. Do not load both copies. Load only relevant indexes and referenced sections, and reuse unchanged context already read.

## Phase Index

### Request triage

| Request | Route |
| --- | --- |
| Analysis, explanation, read-only investigation | Inspect evidence and answer. No task creation or finish ceremony. |
| Clear, bounded, low-risk local edit | Read applicable rules, edit, check and report. A new task is optional unless project lifecycle rules require one. |
| New feature, architecture change, high-risk or multi-session work | Reuse the matching task or create one within the authorized work. Plan before implementation; use the project's formal proposal system. |

For ambiguous complex requests, inspect first and ask only for decisions that change the goal, public contract, cost or risk. State reasonable routine assumptions. A request for analysis alone does not authorize implementation.

### Planning and evidence ownership

- Follow the project's existing authoritative plan system (OpenSpec, Current Plan or lifecycle tree); do not introduce a competing task-status source.
- With OpenSpec, requirements/design/acceptance/checklists belong in the change. Trellis stores execution status, branch/worktree and evidence links. Keep one authoritative checklist.
- `prd.md` can be a short scope/acceptance summary linking the canonical proposal. `design.md` and `implement.md` are needed only for substantial information not already maintained elsewhere; links satisfy the planning requirement if their targets have been read.
- If a local consumer requires an artifact filename, retain a short pointer file rather than duplicate the body. Existing artifacts and history are not deleted by this policy.
- Without a formal proposal system, one concise task document can hold requirements, decisions, steps and validation. Split documents only when that improves review.
- Persist decisions, blockers and verification evidence needed to resume. Do not persist every search result or force a journal entry each turn.
- Parent/child tasks are for independently deliverable work; preserve project lifecycle parentage and explicit dependency ordering.

### Phase routing

- Plan: 1.0 task if needed → 1.1 requirements/decisions → 1.2 research if needed → 1.3 delegation context if needed → 1.4 activate → 1.5 readiness.
- Execute: 2.1 implement → 2.2 check; use 2.3 when evidence requires revisiting the plan.
- Finish: 3.1 verify evidence remains current → 3.2 retrospective if useful → 3.3 durable spec delta if any → 3.4 authorized delivery → 3.5 report.
- Skill routing: `trellis-brainstorm` for unresolved planning; `trellis-before-dev` before edits; `trellis-check` after edits; `trellis-break-loop` for repeated/non-obvious bugs; `trellis-update-spec` for durable contracts; `trellis-session-insight` for missing past decisions; `trellis-meta` for workflow changes. Channel collaboration is opt-in.
- Default to main-session implementation and checking. Delegate only when the user requests parallel work and independent ownership is possible. Respect explicit inline mode and project isolation rules.
- Read details on demand: `python3 .trellis/scripts/get_context.py --mode phase --step <X.Y>`.

[workflow-state:no_task]
Classify this request first. Analysis needs no task; a clear small edit may proceed with applicable rules and checks. For complex work, reuse/create a task only within the user's authorized scope. Do not ask whether to create a task for ordinary conversation. Load relevant context once.
[/workflow-state:no_task]

[workflow-state:planning]
Apply only when this request belongs to the explicitly bound task. Inspect evidence; resolve only consequential open decisions. Read canonical planning documents or their links; avoid duplicate plans. Honor existing implementation authorization after planning is ready. Delegation is opt-in.
[/workflow-state:planning]

[workflow-state:planning-inline]
Apply only when this request belongs to the explicitly bound task. Plan in the main session; read canonical artifacts or their links. Ask only consequential unresolved questions; reuse prior authorization. Skip subagent manifests in inline mode.
[/workflow-state:planning-inline]

[workflow-state:in_progress]
First check whether this request belongs to the explicitly bound task; unrelated analysis preserves its state. For authorized implementation: relevant rules/artifacts → edit → scoped checks and required delivery gates → durable spec delta only if needed → report. Reuse current evidence and prior authorization. No automatic commit, archive or delegation.
[/workflow-state:in_progress]

[workflow-state:in_progress-inline]
First check whether this request belongs to the explicitly bound task; unrelated analysis preserves its state. Main session: relevant rules/artifacts → edit → scoped checks and required delivery gates → durable spec delta if needed → report. Do not dispatch implement/check subagents. Reuse current evidence and prior authorization; no automatic commit/archive.
[/workflow-state:in_progress-inline]

[workflow-state:completed]
Completion metadata does not prove commit, merge, deployment or acceptance. Report actual evidence. Archive only an explicitly authorized, complete target; preserve unrelated tasks and worktrees. Do not infer authorization from this status.
[/workflow-state:completed]

## Phase 1: Plan

#### 1.0 Create task `[conditional · once]`

Check the current request, project lifecycle rules and matching existing tasks. Do not attach work to an unrelated active task. Create a task only when useful/required and within authorization:

```bash
python3 .trellis/scripts/task.py current --source
python3 .trellis/scripts/task.py create "<title>" --slug <slug>
```

Use local `--help` for parent/worktree options. Do not silently switch another session's binding. Do not create duplicate tasks for work already represented in the owning project.

#### 1.1 Requirement exploration `[conditional · repeatable]`

Use `trellis-brainstorm` when meaningful decisions remain. Read code/config/tests before asking for facts. Record the goal, constraints, acceptance and consequential decisions in the canonical plan. Routine implementation choices do not require an interview.

For a complex unreviewed plan, present one concrete proposal for review. If the user has already approved the proposed plan and asked for execution, complete its details and proceed without another ceremonial approval. Stop for new consequential decisions outside that scope.

#### 1.2 Research `[on demand]`

Investigate only unresolved questions. Reuse relevant existing evidence and narrowly retrieve past decisions if needed. Research can run in the main session; it does not require a subagent. Persist findings only when they support a decision or resumption.

#### 1.3 Configure context `[conditional · once]`

Skip manifest curation for inline execution. For authorized delegation, pass the exact task/worktree, role, owned files, relevant artifact/spec links and validation expectations. A worker must not resolve the parent's task by guessing its own session binding.

Use `implement.jsonl` / `check.jsonl` only for the local runtime's supported context references; remove duplicate references, preserve useful existing ones and never use manifests as another plan. Workers implement/check directly and must not recursively spawn those roles.

#### 1.4 Activate task `[conditional · once]`

Once canonical acceptance/design/steps are sufficient and implementation is authorized, run `python3 .trellis/scripts/task.py start <task>` for this session. Do not activate a task merely to answer an unrelated question. No repeated approval for an unchanged approved plan.

#### 1.5 Completion criteria

The plan has testable acceptance, an adequate design and validation approach, and no unresolved decision blocking the authorized next action. Read linked documents before treating pointer artifacts as complete. Preserve project-specific lifecycle and documentation requirements.

## Phase 2: Execute

#### 2.1 Implement `[required for edits · repeatable]`

Load `trellis-before-dev` once for applicable rules and task/canonical artifacts. Work directly in the intended checkout, preserving unrelated changes. Respect package ownership, public contracts and project fail-fast/idempotency rules. Make the smallest coherent change that meets acceptance.

Run relevant checks during iteration. Main-session checking is the default; independent human review required by the project remains required.

#### 2.2 Quality check `[required for edits · repeatable]`

Use `trellis-check`. Determine affected behavior and risk, not just diff length. Test regressions, failure paths, permissions, state transitions and cross-layer contracts where relevant. Do not add a test merely because a wrapper function was added.

During iteration run affected checks. Before the applicable commit/PR/merge gate, complete the project's required full checks, build and runtime evidence. This policy does not exempt mandatory gates.

Reuse a passing result for unchanged code/dependencies/configuration and a suitable unchanged test environment. A skill/phase switch alone is not a reason to rerun. Recheck when relevant inputs change, a failure is fixed or new evidence exposes a gap; report command, scope and result.

Fix failures caused by this work. Distinguish pre-existing or environmental failures; do not expand scope or edit unrelated WIP to make a summary green. Debug a failing check before retrying; escalate only a concrete blocker, not an arbitrary attempt counter.

#### 2.3 Revisit plan `[on demand]`

If implementation reveals an incorrect assumption, update the canonical plan and fix the owning layer. Continue within authorization; ask only if the revised action materially changes scope or risk. Do not revert another contributor's work.

## Phase 3: Finish

#### 3.1 Verify current evidence `[required for edits · once]`

Review 2.2 evidence across the whole intended change. Fill missing required checks; reuse valid results. This is an evidence review, not a mandatory second full test run.

#### 3.2 Debug retrospective `[on demand]`

Use `trellis-break-loop` for repeated or non-obvious failures. Record the root cause and effective prevention once. A routine edit does not need a retrospective.

#### 3.3 Spec update `[on demand]`

Use `trellis-update-spec` only for a new/changed durable contract or convention. Update its existing owner document and link implementation/tests. Do not copy OpenSpec or add a seven-section document for a trivial lesson. If there is no durable delta, no spec write or ritual is required.

#### 3.4 Authorized delivery `[conditional · once]`

Inspect diff/status and identify only this task's files. If commit is authorized, prepare the logical batch, run required pre-commit checks and commit those files. If it is not authorized, report ready/uncommitted; ask only when that next operation is actually needed.

Prior explicit authorization remains valid for the covered operation and scope. Do not re-confirm message wording or an unchanged file grouping. Never stage unrelated files, bypass gates, amend published history or infer push/merge/deploy/provider authorization from permission to edit or commit.

#### 3.5 Wrap-up

Report changes, actual verification and material limitations. Distinguish implementation, local checks, commit, CI, merge, deployment/migration and runtime/human acceptance when relevant; do not list irrelevant stages mechanically.

`trellis-finish-work` reports progress by default. Record a short journal only when requested or useful for resumption. Archive only when the user explicitly authorizes that target and its acceptance is complete. Inspect local `task.py archive --help`, configuration, lifecycle hooks and worktree effects before mutation; suppress unapproved auto-commit/merge/cleanup using supported options. Never promise auto-commits without checking configuration.

## Runtime and maintenance references

- Inspect `.trellis/config.yaml`, relevant spec indexes and the bound task; all project state stays local.
- Task CLI: `python3 .trellis/scripts/task.py --help`; do not guess version-specific flags.
- Phase extraction depends on `## Phase Index`, `## Phase 1: Plan` and `#### X.Y` headings. Per-turn hints depend on paired `[workflow-state:STATUS]` tags; keep them coherent with the steps.
- Keep user-owned local modifications during `trellis update`; do not overwrite template hashes to disguise them as pristine. Reconcile upstream changes before reapplying this policy.
- Historical templates/backups are reference material, not live instructions. Read platform/maintenance details only when changing that integration.
