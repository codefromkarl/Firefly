---
name: trellis-finish-work
description: "Report actual completion and resumption evidence; archive only an explicitly authorized complete target with inspected side effects."
---

# Finish Work

Report progress by default. This skill invocation or a generic request to finish does not by itself authorize commit, archive, merge or worktree cleanup. Reuse explicit authorization already given for named operations and scope.

1. Inspect the matching task, its acceptance evidence and task-owned dirty paths. Preserve unrelated WIP and other sessions' task pointers.
2. Report actual implementation and validation state. A task can be reported locally complete while uncommitted; do not force a commit to provide a useful wrap-up. CI, merge, deployment/migration and runtime/human acceptance remain separate when relevant.
3. Record a short journal only when requested or useful for resumption; use the existing task progress/evidence document where possible. Inspect `add_session.py --help`, project configuration and auto-commit behavior first. Use supported `--no-commit` when commit is not authorized. Do not manufacture a commit hash or duplicate the whole conversation.
4. Archive only if the user explicitly authorized that target and its acceptance is complete. A journal entry or green tests alone is not archive authorization. If incomplete, keep it active and report the specific unmet acceptance.
5. Before archive inspect local `task.py archive --help`, `session_auto_commit`, configured lifecycle hooks, branch/worktree bindings and dirty files. Archive implementations differ across projects. Use supported options to prevent any unapproved commit, merge or cleanup. If a side effect cannot be safely excluded, stop only that mutation and explain the exact side effect.
6. Verify the archive path/status and preserved worktree/unrelated-task state after an authorized archive. Additional tasks require their own covered authorization.

There is no mandatory work/archive/journal commit sequence. `session_auto_commit: false` means scripts do not create commits; never promise otherwise. This skill does not install or modify hooks or guards.
