---
name: trellis-update-spec
description: "Record only new or changed durable contracts in their owning documents, with concise code and test references."
---

# Update Durable Contracts

Use this skill only when implementation/debugging reveals a new or changed contract, convention or reusable failure-prevention rule. No durable delta means no spec write or required retrospective ceremony.

1. Identify the owner: formal product behavior and acceptance in OpenSpec/the existing plan; engineering invariants in project rules; module implementation contracts in the relevant .trellis/spec document. Task progress and one-off evidence stay in the task.
2. Read the current owner document and update it in place. Link canonical documents rather than copying their bodies. Remove obsolete claims only when supported by current evidence.
3. Keep the entry proportional: trigger, required behavior, code/test pointer and any material pitfall are usually enough.
4. For a complex new infrastructure or cross-layer contract, include only needed detail: signatures/data shape, ownership, validation/error semantics, representative success/failure cases and tests. The full seven-part outline is an optional aid, not a mandatory output for every cross-layer edit.
5. Update the index only when routing changed. Verify paths and contracts against the actual code/tests. Avoid broad new bans derived from one incident and do not copy transient run results into permanent conventions.

Do not edit global model memory stores through this skill. Respect project isolation and the user's separate memory-update authorization requirements.
