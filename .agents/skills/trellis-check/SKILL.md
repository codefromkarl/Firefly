---
name: trellis-check
description: "Verify affected behavior and required project gates using current evidence, without mechanical tests or unrelated fixes."
---

# Check Changes

1. Identify this task's changes with git status/diff, including relevant untracked files. Separate pre-existing WIP; never silently review/fix all dirty files as this task.
2. Read applicable project rules and canonical acceptance/design contracts, following task links. Reuse unchanged context. Load relevant package Quality Check sections; risk depends on behavior, not line count.
3. During iteration run affected lint/type checks/tests. Cover meaningful regressions, error paths, permissions, state transitions and cross-layer contracts. Do not add tests merely for new wrapper functions, and do not mirror implementation.
4. At the applicable commit/PR/merge boundary complete all mandatory project checks, full suites, builds and runtime evidence. A lightweight workflow does not waive these gates or required independent human review.
5. Reuse passing results only for unchanged relevant code, dependencies, configuration and an appropriate unchanged environment. A skill/phase switch alone does not invalidate evidence. Rerun affected checks after fixes or new findings.
6. Review ownership, data flow, imports, error handling and duplicated domain concepts where the change requires it. Search existing patterns with rg; do not extract a shared abstraction solely because two literal values match.
7. Fix findings caused by this task. Classify pre-existing/environmental failures and report them without expanding scope or weakening gates. Investigate before retrying; continue useful diagnosis while possible.
8. Report commands, scope, results and missing evidence honestly. Update an existing spec only for a durable contract delta.

Main-session checking is the default. A read-only review stays read-only unless fixes are authorized. Local green, CI, merge, deployment and runtime/human acceptance are separate facts.
