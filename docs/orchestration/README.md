# Orchestration Layer

A reusable way to build features (and run other multi-agent jobs) on Staffeer with the right model on
each task, a human in the loop at the gates the repo mandates, and a full record of how every agent
performed.

Two pieces, cleanly separated:

- **The orchestrator** (`/orchestrate`) — a thin, **workflow-agnostic** driver. It discovers
  self-describing workflows, gathers their declared inputs, drives them stage-by-stage per an autonomy
  mode, surfaces approval gates, enforces the model-usage guideline, and logs every agent invocation.
  It contains **no workflow-specific logic** and **never writes feature code**.
- **Workflows** — each owns *all* the logic for one kind of job. The first is **`build-feature`**.
  Future workflows (e.g. a validation-signal-driven `review`, a `migrate`, an `eval-sweep`) plug into
  the same contract and the orchestrator drives them unchanged.

```
/orchestrate <workflow> <input> [mode]      ← Opus; generic manager + ledger
        │  reads meta.orchestrator (manifest), drives one stage at a time
        ▼
docs/orchestration/workflows/<name>.js      ← JS Workflow-engine script; owns the logic
        │  spawns sub-agents — ONE atomic instruction each (haiku/sonnet by model-usage.md)
        ▼
.claude/orchestration/logs/<date>/<runId>/  ← per-run JSON ledger (git-ignored runtime)
```

This is the repo's hexagonal shape applied to process: `/orchestrate` is a **driving adapter**, the
workflow is the **use-case logic**, sub-agents are **workers**, and the ledger is an **output port**.

## Documents

- [`workflow-contract.md`](workflow-contract.md) — the binding interface every workflow implements
  (manifest, stage protocol, return envelope). Read this to add a workflow.
- [`model-usage.md`](model-usage.md) — which model plays which role, and why.
- [`ledger-schema.md`](ledger-schema.md) — per-run log layout and record shapes.
- [`workflows/`](workflows/) — the workflow scripts. `build-feature.js` is the first.

## Autonomy modes

| Mode | Gates | Use when |
|---|---|---|
| `gate` (default) | Pause for human approval at **every** gate (spec, architecture/ADR, commit). | Normal use; honours `task-execution.md`. |
| `checkpoint` | Auto-approve intermediate gates; pause **once** before commit. | You trust the slice and want fewer interruptions. |
| `autonomous` | No pauses; commit on a branch. | Low-risk, well-scoped work; maximum throughput. |

A failure that exhausts bounded auto-repair (`maxRepairAttempts`, default 2) **always** escalates to a
human, regardless of mode.

## Usage

```bash
/orchestrate                                   # list discovered workflows, then pick one
/orchestrate build-feature docs/tasks/02-beach-matching.md        # default: gate mode
/orchestrate build-feature docs/tasks/03-skill-matching.md checkpoint
/build-feature docs/tasks/02-beach-matching.md                    # shortcut for build-feature
```

## The `build-feature` workflow

A single fixed pipeline (the Spec stage self-skips when the slice changes no contract):

1. **Spec** *(gate)* — author the `## Spec` + contract-test outline; approve before any code (SDD RULE-001).
2. **Decompose** — task bullets → ordered atomic instructions (one coherent edit to one file each).
3. **Eval & tests first** — golden-table scenario evals + failing contract/unit tests, run to confirm they fail.
4. **Implement** — one agent per atomic instruction; `haiku` for mechanical, `sonnet` for logic.
5. **Quality gate** — `make format/test/lint`; bounded auto-repair on failure.
6. **Verify / review** — adversarial check vs acceptance criteria + binding rules; findings → repair.
7. **Architecture verification + ADR** *(gate)* — check hexagonal/ports/LikeC4 deviation; draft an ADR on a deliberate change.
8. **Progress report** — update `progress.html` with the slice's status.
9. **Finalize** *(gate)* — mark the task `[x]`; Conventional Commit / PR.

## Adding a new workflow

See [`workflow-contract.md`](workflow-contract.md#4-how-to-add-a-workflow). In short: drop a new
`docs/orchestration/workflows/<name>.js` with a `meta.orchestrator` manifest and stages that return the
standard envelope. `/orchestrate <name>` picks it up automatically — no orchestrator changes.

## Installing the slash commands locally

Slash commands must live in `.claude/commands/` (git-ignored, local). The tracked source of truth is
`docs/commands/*.{md,toml}`. Install/refresh the local copies with:

```bash
make sync-claude
```
