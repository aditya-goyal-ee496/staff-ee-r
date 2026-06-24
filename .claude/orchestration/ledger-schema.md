# Ledger Schema

Every workflow run the orchestrator drives is logged to its own files, organised by **date** and a
**unique run id**. The orchestrator (the main loop) mints the id at run start via Bash, because the
sandboxed workflow engine cannot call `Date.now()` / `Math.random()`:

```
runId = <workflow>-<YYYY-MM-DDTHH-MM-SS>-<6-char>     # e.g. build-feature-2026-06-24T10-15-03-a1b2c3
```

## Layout (runtime — git-ignored, under `.claude/`)

```
.claude/orchestration/logs/
  <YYYY-MM-DD>/
    <runId>/
      ledger.jsonl     # append-only; ONE record per agent invocation
      summary.json     # one object; the run rollup, written at finalize
      gates/           # gate artifacts surfaced this run (spec/ADR drafts, diffs) for audit
  index.jsonl          # one line per run, across all dates
```

`.claude/` is git-ignored, so runtime logs are never committed. This schema doc (and the sample under
`sample-run/`) is the committed contract for their shape.

## `ledger.jsonl` — one record per agent invocation

```json
{
  "runId": "build-feature-2026-06-24T10-15-03-a1b2c3",
  "ts": "2026-06-24T10:15:42Z",
  "workflow": "build-feature",
  "stage": "implement",
  "agentLabel": "impl:eligibility.location_constraint",
  "model": "sonnet",
  "effort": "medium",
  "atomicInstruction": "Implement location_constraint in domain/eligibility.py handling the four location cases.",
  "complexityTag": "logic",
  "status": "ok",
  "attempts": 1,
  "verdict": { "pass": true, "issues": [] },
  "filesTouched": ["src/staffeer/domain/eligibility.py"]
}
```

Field notes:
- `ts` — stamped by the orchestrator when it writes the row (the workflow returns rows without `ts`).
- `status` — `ok` | `failed` | `skipped`.
- `attempts` — includes bounded auto-repair retries (so `attempts > 1` flags a stage that needed repair).
- `verdict.issues` — present when a verifier/reviewer raised findings.

## `summary.json` — one per run

```json
{
  "runId": "build-feature-2026-06-24T10-15-03-a1b2c3",
  "workflow": "build-feature",
  "input": "docs/tasks/02-beach-matching.md",
  "mode": "gate",
  "startedAt": "2026-06-24T10:15:03Z",
  "endedAt": "2026-06-24T10:31:20Z",
  "outcome": "completed",
  "gates": [
    { "stage": "spec", "decision": "approved" },
    { "stage": "architecture", "decision": "approved", "adr": "docs/adr/003-..." },
    { "stage": "finalize", "decision": "approved", "commit": "feat(matching): ..." }
  ],
  "agentsByModel": { "opus": 0, "sonnet": 7, "haiku": 3 },
  "repairs": 1,
  "passRate": 1.0
}
```

`outcome` — `completed` | `escalated` | `aborted`.

## `index.jsonl` — one line per run

```json
{ "runId": "build-feature-2026-06-24T10-15-03-a1b2c3", "date": "2026-06-24", "workflow": "build-feature", "input": "docs/tasks/02-beach-matching.md", "mode": "gate", "outcome": "completed" }
```

`/orchestrate` reads `index.jsonl` to list and summarise past runs.
