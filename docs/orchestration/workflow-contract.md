# Workflow Contract

The **orchestrator** (`/orchestrate`) is a thin, workflow-agnostic driver. It knows *nothing* about
any specific workflow's logic. Every workflow it can run is **self-describing** and speaks one small,
fixed contract. Adding a new workflow (e.g. a validation-signal-driven `review`, a `migrate`, an
`eval-sweep`) means writing one new script that satisfies this contract — **the orchestrator needs no
changes**.

Workflows are JS scripts for the built-in Workflow engine, kept under
`docs/orchestration/workflows/<name>.js` (tracked) and invoked by the orchestrator via the Workflow
tool's `scriptPath`. The engine sandbox has **no filesystem access** and **no `Date.now()` /
`Math.random()`** — so a workflow never writes the ledger itself; it *returns* data and the
orchestrator (the main loop) stamps timestamps and writes files.

## 1. Self-description (manifest)

Every workflow script begins with an `export const meta` literal carrying an `orchestrator` block:

```js
export const meta = {
  name: 'build-feature',
  description: 'Build one task-list slice into reviewed, tested, architecture-checked code.',
  phases: [ /* engine progress groups — one per phase() call */ ],
  orchestrator: {
    // What the orchestrator must gather and pass in as args before stage 1.
    inputs: [
      { key: 'taskFilePath', source: 'arg' },                 // from the command argument
      { key: 'taskFileText', source: 'file:taskFilePath' },   // file contents the orchestrator reads
    ],
    // The ordered stages the orchestrator drives, one invocation each.
    stages: [
      { id: 'spec',         isGate: true,  gateArtifact: 'spec',    models: ['sonnet'] },
      { id: 'decompose',    isGate: false,                          models: ['sonnet'] },
      { id: 'tests',        isGate: false,                          models: ['sonnet'] },
      { id: 'implement',    isGate: false,                          models: ['haiku', 'sonnet'] },
      { id: 'quality',      isGate: false,                          models: ['sonnet'] },
      { id: 'verify',       isGate: false,                          models: ['sonnet'] },
      { id: 'architecture', isGate: true,  gateArtifact: 'adr',     models: ['sonnet'] },
      { id: 'report',       isGate: false,                          models: ['haiku'] },
      { id: 'finalize',     isGate: true,  gateArtifact: 'commit',  models: [] },
    ],
    maxRepairAttempts: 2,   // bounded auto-repair before escalating to a human
    emitsLedger: true,      // orchestrator records one ledger row per agent invocation
    commits: true,          // a successful run ends in a Conventional Commit / PR
  },
}
```

The orchestrator reads this block (it scans `docs/orchestration/workflows/*.js`) to learn **what
inputs to gather, which stages are gates, and what models will run** — without knowing what any stage
*does*. It also checks each stage's declared `models` against `docs/orchestration/model-usage.md` and
warns on a violation.

## 2. Stage protocol

The orchestrator invokes the workflow **one stage at a time** (the headless engine cannot pause
mid-script for human input). It passes the requested stage and any prior approved artifacts back in:

```js
Workflow({
  scriptPath: 'docs/orchestration/workflows/build-feature.js',
  args: {
    stage: 'implement',                 // which stage to run now
    mode: 'gate',                       // gate | checkpoint | autonomous
    runId: 'build-feature-2026-06-24T10-15-03-a1b2c3',
    maxRepairAttempts: 2,
    taskFilePath: 'docs/tasks/02-beach-matching.md',
    taskFileText: '…',
    prior: {                            // approved outputs of earlier stages
      spec: { /* approved spec */ },
      atomicInstructions: [ /* approved decomposition */ ],
    },
  },
})
```

A workflow stage must be **idempotent given its `args`** so a run can resume after an approval pause.

## 3. Standard return envelope

Every stage of every workflow returns the same shape. This is what makes the ledger writer and gate
handler workflow-agnostic:

```js
return {
  stage: 'implement',
  records: [                            // ONE per agent invocation this stage
    {
      agentLabel: 'impl:eligibility.location_constraint',
      model: 'sonnet',
      effort: 'medium',
      atomicInstruction: 'Implement location_constraint in domain/eligibility.py …',
      complexityTag: 'logic',           // 'mechanical' | 'logic'
      status: 'ok',                     // 'ok' | 'failed' | 'skipped'
      attempts: 1,
      verdict: { pass: true, issues: [] },
      filesTouched: ['src/staffeer/domain/eligibility.py'],
    },
  ],
  summary: { /* freeform per-stage rollup */ },
  // Non-null when the orchestrator must surface something to a human before continuing.
  gate: {
    needsApproval: true,
    kind: 'spec' | 'adr' | 'commit' | 'failure',
    artifact: { /* the thing a human reviews: spec text, ADR draft, diff, failure detail */ },
  } | null,
  // The next stage to run, or null when the workflow is complete.
  nextStage: 'quality' | null,
}
```

### Gate semantics by mode

| Mode | Behaviour at an `isGate` stage with `gate.needsApproval` |
|---|---|
| `gate` (default) | Pause and require human approval at **every** gate before the next stage. |
| `checkpoint` | Auto-approve intermediate gates; pause **once** before the `commit` gate. |
| `autonomous` | Never pause; proceed through all gates (still records everything). |

A `gate.kind === 'failure'` (e.g. bounded auto-repair exhausted) **always** escalates to a human,
regardless of mode.

## 4. How to add a workflow

1. Create `docs/orchestration/workflows/<name>.js` with the `meta.orchestrator` block above.
2. Implement each declared stage; branch on `args.stage`; return the standard envelope.
3. Choose per-agent models from `docs/orchestration/model-usage.md`; give every `agent()` an explicit
   `label`, `phase`, `model`, and `effort`.
4. Keep each agent to **exactly one atomic instruction**.
5. That's it — `/orchestrate <name> <input>` now discovers and drives it. No orchestrator edits.
