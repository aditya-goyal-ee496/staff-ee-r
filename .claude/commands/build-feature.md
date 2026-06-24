---
allowed-tools: Workflow, Bash, Read, Write, AskUserQuestion
argument-hint: "[task-file] [mode]"
description: Build one docs/tasks/*.md slice into reviewed, tested, architecture-checked code via the build-feature workflow (shortcut for /orchestrate build-feature)
---

## Build Feature

Shortcut for `/orchestrate build-feature <task-file> [mode]`. Runs the **build-feature** workflow on a
single task-list slice without the workflow-selection step. Everything else is identical to
`/orchestrate`: you run on Opus, drive the workflow stage-by-stage, honour its gates, enforce the
model-usage guideline, and log every agent to a per-run JSON ledger.

## Usage

```
/build-feature docs/tasks/02-beach-matching.md            # default mode: gate
/build-feature docs/tasks/03-skill-matching.md checkpoint
```

If no `task-file` is given, list `docs/tasks/*.md` and ask which slice to build (AskUserQuestion).
`mode` ∈ `gate` (default) | `checkpoint` | `autonomous`.

## Process

Follow the `/orchestrate` process (`.claude/commands/orchestrate.md`) with the workflow fixed to
`build-feature`:

1. Read `.claude/orchestration/workflows/build-feature.js` `meta.orchestrator` for its stages and inputs.
2. Read the task file; that text is the `taskFileText` input.
3. Mint a dated, unique run id + log dir under `.claude/orchestration/logs/`.
4. Pick the mode (default `gate`).
5. On a `feat/<slice>` branch (never `main`), drive the stages — **spec → decompose → tests →
   implement → quality → verify → architecture → report → finalize** — invoking the workflow once per
   stage via the Workflow tool's `scriptPath`, appending records to the ledger, and handling each
   gate per the mode.
6. Finalize: write the run summary + index line, commit per git-rules if approved, and print the
   per-agent performance report.

The build-feature stage shape and its gates are documented in `.claude/orchestration/README.md`.

## Guidelines

DO: honour the spec, architecture/ADR, and commit gates in `gate` mode; keep each worker to one
atomic instruction; record every agent.
DON'T: write feature code yourself; weaken or skip the eval-first tests; mark a task `[x]` that isn't
actually done and green; commit to `main`.
