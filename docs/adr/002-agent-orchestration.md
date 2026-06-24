# ADR-002: Agent orchestration via a generic orchestrator + self-describing workflows

## Status: Accepted

## Context

Staffeer is built eval-first and vertically sliced, with a strict task-execution loop
(`CLAUDE.md (Development workflow)`): spec → contract test → simplest impl → `make format/test/lint` →
human review → mark `[x]` → commit. Driving that loop entirely by hand, one slice at a time, with a
single agent, is slow and leaves no record of *how* each step was produced. We also expect more
kinds of multi-agent jobs over time (a validation-signal-driven review, migrations, eval sweeps), so
a one-off automation would not pay off.

We want: the right model on each task (cheap models for mechanical edits, capable models where
judgement compounds), the repo's approval gates kept intact, one atomic instruction per worker so
cheap models stay effective, and a full per-run audit trail — without baking any specific job's logic
into the driver.

The pre-selected harness already provides a JS Workflow engine (deterministic fan-out / pipeline of
sub-agents with per-agent model selection) and a sub-agent (`Agent`) tool. The engine sandbox has no
filesystem access and cannot generate timestamps or randomness.

## Decision

Adopt a **two-part orchestration layer**: a thin, **workflow-agnostic orchestrator** plus
**self-describing workflows**, connected by a small fixed **Workflow Contract**
(`.claude/orchestration/workflow-contract.md`).

- **Orchestrator** — the `/orchestrate` slash command, run on **Opus**. It discovers workflows
  (`.claude/orchestration/workflows/*.js`), reads each one's `meta.orchestrator` manifest, gathers
  declared inputs, drives the workflow **one stage at a time** via the Workflow engine's `scriptPath`,
  adjudicates gates per an autonomy mode, enforces the model-usage guideline, and writes the ledger.
  It contains **no workflow-specific logic and never writes feature code**.
- **Workflows** — JS Workflow-engine scripts that own *all* the logic for one job. Each declares a
  manifest (inputs, stages, which are gates, per-stage models, `maxRepairAttempts`, `commits`) and
  returns a standard envelope (`records`, `summary`, `gate`, `nextStage`) from every stage. The first
  is **`build-feature`** (`.claude/orchestration/workflows/build-feature.js`): spec → decompose → tests
  (eval-first) → implement → quality → verify → architecture/ADR → progress report → finalize.
- **Model tiers** (`.claude/orchestration/model-usage.md`): Opus orchestrates; Sonnet plans, specs,
  tests, reviews, and does logic-bearing edits; Haiku does mechanical single-file edits and the
  progress-report update; the quality gate is deterministic Bash. Workflows pick per-agent models from
  these tiers; the orchestrator warns on a declared violation.
- **Single atomic instruction per agent** — within a workflow, each spawned agent gets exactly one
  coherent edit to one file. Same-file instructions are sequenced; cross-file ones run in parallel.
- **Autonomy modes** — `gate` (default; pause at every gate, honouring `CLAUDE.md → Development workflow`),
  `checkpoint` (pause once before commit), `autonomous` (no pauses). A failure that exhausts
  **bounded auto-repair** always escalates to a human regardless of mode.
- **Per-run JSON ledger** — the orchestrator mints a dated, unique `runId` (Bash, since the sandbox
  can't) and logs one record per agent invocation under
  `.claude/orchestration/logs/<date>/<runId>/` (`ledger.jsonl`, `summary.json`, `gates/`) plus an
  `index.jsonl`. Shapes in `.claude/orchestration/ledger-schema.md`.

Because `.claude/` is git-ignored, the **tracked source of truth lives under `docs/`** (workflow
scripts under `.claude/orchestration/workflows/`, command definitions under `.claude/commands/`); slash
commands are installed locally into `.claude/commands/` via `make sync-claude`, and runtime logs stay
in `.claude/` uncommitted.

## Consequences

- Adding a new workflow is a self-contained change: drop a `.claude/orchestration/workflows/<name>.js`
  satisfying the contract; `/orchestrate <name>` drives it with **no orchestrator edits**.
- The approval gates the repo mandates (spec before code, architecture/ADR, commit) are enforced by
  the default `gate` mode; teams can trade oversight for throughput per run via the mode.
- Every run is auditable: which model did what, how many attempts, what each reviewer found.
- Cost is controlled by pushing mechanical work to Haiku and reserving Opus for orchestration.
- The orchestrator must drive stages serially (the headless engine can't pause mid-script), so a
  gated run is a sequence of stage invocations with approvals between — slightly more orchestration
  overhead in exchange for human-in-the-loop control.
- Spec/architecture changes still go through the normal SDD approval; the workflow surfaces them as
  gate artifacts rather than deciding unilaterally.

## Alternatives considered

- **A single end-to-end headless workflow** (no separate orchestrator). Rejected: the engine can't
  pause for the human approval gates the repo requires, and it would couple job logic to the driver.
- **A bespoke Python orchestration harness.** Rejected for the POC: more to build and maintain, and it
  duplicates what the Workflow engine + Agent tool already provide.
- **Hard-coding the build-feature pipeline into the command.** Rejected: it would not generalise to
  the review/migrate/eval workflows we expect next.
