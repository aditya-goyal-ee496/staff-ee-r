# Model-Usage Guideline

The orchestration layer spends the most capable (and expensive) model only where judgement compounds,
and pushes mechanical work down to cheaper, faster models. This is the single source of truth for
which model plays which role. Workflows **declare** their per-stage models in `meta.orchestrator`
(see `workflow-contract.md`); the orchestrator checks declarations against this table and warns on a
violation.

## Tiers

| Role | Model | Effort | Why this tier |
|---|---|---|---|
| **Orchestrator** (`/orchestrate` main loop) | **opus** | high | Dependency resolution, gate adjudication, reading manifests, deciding when to escalate. **Never writes feature code.** |
| **Decomposer / planner** | sonnet | medium | Turns one task bullet into an ordered list of atomic instructions. Needs judgement, not depth. |
| **Spec author** | sonnet | high | Drafts the `## Spec` (contract, invariants, acceptance criteria, error mapping). Gate-bounded; correctness matters. |
| **Eval / test author** | sonnet | medium | Writes golden-table scenario evals + failing contract/unit tests from the spec. |
| **Implementation worker — `mechanical`** | **haiku** | low | One boilerplate edit: a value object, a stub, a single trivial function. No cross-cutting reasoning. |
| **Implementation worker — `logic`** | sonnet | medium | One logic-bearing edit: a constraint, a scorer, a ranker. |
| **Verifier / reviewer** | sonnet | high | Adversarial check of one change against its acceptance criterion and the binding rules. |
| **Architecture verifier** | sonnet | high | Diffs the result against hexagonal/ports-adapters rules + the LikeC4 model; drafts an ADR on a deliberate change. |
| **Repair (fix) worker** | sonnet | medium | Targeted fix from a concrete failure signal (test output, lint error, review finding). Bounded retries. |
| **Progress reporter** | **haiku** | low | Updates `progress.html` status — mechanical doc edit. |
| **Quality gate** (`make format/test/lint`) | — (Bash) | — | Deterministic; no model. |

## Principles

1. **One atomic instruction per agent.** Every spawned agent receives exactly one self-contained
   instruction — one coherent edit to one file. This keeps cheap models effective and makes each
   ledger row meaningful.
2. **Opus orchestrates, never implements.** The orchestrator plans, drives, and adjudicates gates.
   All code, ADRs, and report edits come from sub-agents (and show up in the ledger).
3. **Match model to the work, not the stage.** The Implement stage picks `haiku` vs `sonnet` per
   instruction from its `complexityTag`, so a slice of mostly-boilerplate edits stays cheap.
4. **Escalate, don't downgrade quality.** Bounded auto-repair uses `sonnet`; if it can't fix the
   failure within `maxRepairAttempts`, escalate to a human rather than accept a worse result.

## Model ids

Use the model aliases the Agent/Workflow tools accept: `opus`, `sonnet`, `haiku`. The current
generation behind these aliases is Opus 4.8 / Sonnet 4.6 / Haiku 4.5 — see the `claude-api` skill for
exact ids and pricing if you need them.
