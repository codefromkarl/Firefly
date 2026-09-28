---
name: trellis-before-dev
description: "Read relevant local rules and canonical task contracts before editing, without duplicate context loading."
---

# Before Editing

1. Confirm this request's scope, authorization and owning checkout; preserve unrelated WIP and active tasks.
2. Read the project's AGENTS.md and applicable rules. If Trellis is absent, use the existing workflow; do not scaffold it automatically.
3. For a matching task, read its PRD and relevant design/implementation material, following links to the project's canonical plan. Missing optional files are not a reason to manufacture duplicate documents. A small task need not have a Trellis directory unless the project requires it.
4. Discover relevant package/layer indexes with `python3 .trellis/scripts/get_context.py --mode packages` when available. Read the applicable pre-development sections and referenced contracts. Load shared guides only when relevant.
5. Check ownership, affected public behavior and validation expectations, then edit within the authorized scope. Reuse unchanged materials already read; reload when changed or missing after context compaction.

Project-local skills take precedence over global fallbacks. Preserve project-specific lifecycle, isolation and release gates. Inline mode implements directly and needs no subagent context manifests.
