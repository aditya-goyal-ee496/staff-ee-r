---
allowed-tools: Workflow, Bash, Read, Write, AskUserQuestion
argument-hint: "[workflow] [input] [mode]"
description: Generic, workflow-agnostic orchestrator — discovers and drives a self-describing workflow stage-by-stage, honours its gates, enforces model-usage guidelines, and logs every agent to a per-run JSON ledger
---

## Orchestrate

Drive any self-describing workflow to completion. You (the orchestrator) run on **Opus**: you plan,
gather inputs, drive stages, adjudicate gates, and record performance — **you never write feature
code yourself**. All logic lives in the workflow; you know only the contract in
`docs/orchestration/workflow-contract.md`.

## Usage

```
/orchestrate                                          # list workflows, then pick one
/orchestrate [workflow] [input] [mode]
/orchestrate build-feature docs/tasks/02-beach-matching.md          # default mode: gate
/orchestrate build-feature docs/tasks/03-skill-matching.md checkpoint
```

`mode` ∈ `gate` (default) | `checkpoint` | `autonomous`. If `workflow`/`input`/`mode` are missing,
ask via AskUserQuestion.

## When to use

- To build a task-list slice end-to-end (`build-feature`) with the right model on each step, the
  repo's approval gates honoured, and a full audit trail.
- To run any future workflow (`review`, `migrate`, `eval-sweep`, …) the same way — adding one needs
  **no change to this command**.

## Process

### Step 1 — Resolve the workflow
List candidates with `ls docs/orchestration/workflows/*.js`. Read the chosen file's
`export const meta` literal and extract `meta.orchestrator` (its `inputs`, `stages`,
`maxRepairAttempts`, `emitsLedger`, `commits`). If no workflow arg was given, present the discovered
workflows (name + description) via AskUserQuestion. **Do not invent a workflow** — only run a file
that exists.

### Step 2 — Check the model guideline
For each stage's declared `models`, cross-check against `docs/orchestration/model-usage.md`. If a
stage declares a model outside its allowed tier, warn the user before proceeding (don't block).

### Step 3 — Gather declared inputs
For each entry in `meta.orchestrator.inputs`: `source:'arg'` comes from the command argument;
`source:'file:<key>'` means **you** read that file and pass its text. Collect everything the first
stage needs.

### Step 4 — Mint the run id and prepare logging
Run Bash to create a unique, dated run id and its log dir:
```
DATE=$(date +%F); TS=$(date +%FT%H-%M-%S); RID="<workflow>-$TS-$(uuidgen | tr 'A-Z' 'a-z' | cut -c1-6)"
mkdir -p ".claude/orchestration/logs/$DATE/$RID/gates"
```
Keep `RID`, `DATE`, and the log dir for the whole run. (The workflow can't make timestamps; you own them.)

### Step 5 — Pick the autonomy mode
Default `gate`. If not passed, ask via AskUserQuestion (gate / checkpoint / autonomous) — explain that
`gate` honours every approval gate, `checkpoint` pauses once before commit, `autonomous` never pauses.

### Step 6 — Branch if the workflow commits
If `meta.orchestrator.commits` is true, ensure you are on a `feat/<slice>` branch (or the current
worktree) — **never operate on `main`** (`docs/rules/git-rules.md`).

### Step 7 — Drive the stages
Walk `meta.orchestrator.stages` in order, starting at the first stage (or a resume point). For each stage:
1. Invoke the workflow for exactly that stage:
   ```
   Workflow({ scriptPath: "docs/orchestration/workflows/<workflow>.js",
              args: { stage, mode, runId: RID, maxRepairAttempts,
                      ...gatheredInputs, prior: approvedArtifacts } })
   ```
2. **Append the returned `records`** to `.claude/orchestration/logs/$DATE/$RID/ledger.jsonl`, one JSON
   object per line, adding `runId`, `ts` (`date -u +%FT%TZ`), `workflow`, and `stage` to each (see
   `docs/orchestration/ledger-schema.md`).
3. If the envelope has `gate.needsApproval`:
   - `kind:'failure'` → **always** stop and escalate to the human with the artifact (bounded
     auto-repair was exhausted inside the workflow).
   - otherwise apply the mode: **gate** → save the artifact under `…/$RID/gates/`, show it, and ask
     the human to approve/revise via AskUserQuestion before continuing; **checkpoint** → auto-approve
     unless `kind:'commit'` (pause once there); **autonomous** → auto-approve all.
   - On approval, add the artifact to `prior` for later stages; on revision, re-invoke the same stage
     with the feedback.
4. Advance to `nextStage`; stop when it is `null`.

### Step 8 — Finalize
- Write `.claude/orchestration/logs/$DATE/$RID/summary.json` and append one line to
  `.claude/orchestration/logs/index.jsonl` (shapes in `ledger-schema.md`).
- If the workflow `commits` and the commit gate was approved, commit per `docs/rules/git-rules.md`
  (Conventional Commit; never to `main`).
- **Print a performance summary**: per agent — label, model, attempts, status, verdict; plus
  per-model counts, repair count, and pass rate. Point to the run's log dir.

## Guidelines

DO: stay generic — drive purely off `meta.orchestrator` + the returned envelope; honour every gate in
`gate` mode; record every agent; warn on model-guideline violations.
DON'T: write feature code; branch on the workflow's name or hard-code its stages; skip the ledger;
commit to `main`; mark a task `[x]` the workflow didn't actually complete.

## Workflow Summary
1. Resolve the workflow and read its manifest.
2. Check declared models against the guideline.
3. Gather declared inputs.
4. Mint a dated, unique run id + log dir.
5. Pick the autonomy mode (default gate).
6. Branch if the workflow commits.
7. Drive stages one at a time; log records; handle gates by mode.
8. Write summary + index, commit if approved, print the per-agent performance report.
