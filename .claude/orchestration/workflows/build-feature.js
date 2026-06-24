// build-feature — turn one docs/tasks/*.md slice into reviewed, tested, architecture-checked code.
//
// Driven by /orchestrate one STAGE at a time (see .claude/orchestration/workflow-contract.md). The
// engine sandbox has no filesystem access and no Date.now()/Math.random(): sub-agents do all file
// edits; this script only returns data and the orchestrator stamps timestamps + writes the ledger.
//
// Every stage branches on A.stage and returns the standard envelope:
//   { stage, records[], summary, gate|null, nextStage|null }

export const meta = {
  name: 'build-feature',
  description: 'Build one task-list slice into reviewed, tested, architecture-checked code + a progress report.',
  phases: [
    { title: 'spec' }, { title: 'decompose' }, { title: 'tests' }, { title: 'implement' },
    { title: 'quality' }, { title: 'verify' }, { title: 'architecture' }, { title: 'report' },
    { title: 'finalize' },
  ],
  orchestrator: {
    inputs: [
      { key: 'taskFilePath', source: 'arg' },
      { key: 'taskFileText', source: 'file:taskFilePath' },
    ],
    stages: [
      { id: 'spec',         isGate: true,  gateArtifact: 'spec',   models: ['sonnet'] },
      { id: 'decompose',    isGate: false,                         models: ['sonnet'] },
      { id: 'tests',        isGate: false,                         models: ['sonnet'] },
      { id: 'implement',    isGate: false,                         models: ['haiku', 'sonnet'] },
      { id: 'quality',      isGate: false,                         models: ['sonnet'] },
      { id: 'verify',       isGate: false,                         models: ['sonnet'] },
      { id: 'architecture', isGate: true,  gateArtifact: 'adr',    models: ['sonnet'] },
      { id: 'report',       isGate: false,                         models: ['haiku'] },
      { id: 'finalize',     isGate: true,  gateArtifact: 'commit', models: [] },
    ],
    maxRepairAttempts: 2,
    emitsLedger: true,
    commits: true,
  },
}

// ---------------------------------------------------------------------------------------------------
// Shared context appended to every worker prompt so cheap models stay grounded in the binding rules.
const RULES_CONTEXT = `
Binding rules (.claude/principles/): hexagonal architecture (domain core has NO I/O; depend through ports);
clean-code (functions < 20 lines, intention-revealing names, no dead code); testing-principles
(one assertion/test, AAA, no mocking domain logic); security (PII scrubbed before any LLM call,
never log PII/secrets); code-quality (specific errors, structured logging only). Ubiquitous language:
beach, roll-off, new joiner, co-location, Chennai-open. Do the SIMPLEST thing that passes the test.`

const taskRef = (a) => `Task file: ${a.taskFilePath}\n\n${a.taskFileText}`
const specRef = (a) => (a.prior && a.prior.spec ? `\nApproved spec:\n${JSON.stringify(a.prior.spec)}` : '')

const ATOMIC_SCHEMA = {
  type: 'object',
  required: ['changesContract', 'instructions'],
  properties: {
    changesContract: { type: 'boolean' },
    instructions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'file', 'instruction', 'complexityTag', 'acceptanceCriterion'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          file: { type: 'string' },
          symbol: { type: 'string' },
          instruction: { type: 'string' },
          complexityTag: { enum: ['mechanical', 'logic'] },
          dependsOn: { type: 'array', items: { type: 'string' } },
          acceptanceCriterion: { type: 'string' },
        },
      },
    },
  },
}

const WORK_SCHEMA = {
  type: 'object',
  required: ['status', 'summary', 'filesTouched'],
  properties: {
    status: { enum: ['ok', 'failed', 'skipped'] },
    summary: { type: 'string' },
    filesTouched: { type: 'array', items: { type: 'string' } },
    issues: { type: 'array', items: { type: 'string' } },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['pass', 'issues'],
  properties: { pass: { type: 'boolean' }, issues: { type: 'array', items: { type: 'string' } } },
}

const QUALITY_SCHEMA = {
  type: 'object',
  required: ['pass', 'failures'],
  properties: {
    pass: { type: 'boolean' },
    failures: { type: 'array', items: { type: 'string' } },
    output: { type: 'string' },
  },
}

const ARCH_SCHEMA = {
  type: 'object',
  required: ['classification', 'rationale'],
  properties: {
    classification: { enum: ['conformant', 'unintended-deviation', 'deliberate-change'] },
    rationale: { type: 'string' },
    deviations: { type: 'array', items: { type: 'string' } },
    adrPath: { type: 'string' },
    adrTitle: { type: 'string' },
    likeC4ChangeNeeded: { type: 'boolean' },
  },
}

const rec = (o) => ({ effort: 'medium', complexityTag: null, attempts: 1, verdict: { pass: true, issues: [] }, filesTouched: [], ...o })
const envelope = (stage, records, summary, gate, nextStage) => ({ stage, records, summary, gate: gate || null, nextStage: nextStage || null })

// ---------------------------------------------------------------------------------------------------
const DEFAULT_MAX_REPAIR = 2   // mirrors meta.orchestrator.maxRepairAttempts (meta is export-only; not in body scope)
// The engine may deliver `args` as a JSON string; normalise to an object so the orchestrator can pass
// a plain object and the script still works either way.
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})
const stage = A.stage
const maxRepair = A.maxRepairAttempts || DEFAULT_MAX_REPAIR
phase(stage)

// === spec ==========================================================================================
if (stage === 'spec') {
  const r = await agent(
    `You are authoring a SPEC for a Staffeer task slice, per .claude/commands/specify.md.
First decide: does this slice introduce or change a CONTRACT (a port Protocol, a domain model/value
object, or a shared shape like ScoreContribution)? If NOT, set changesContract=false and return an
empty instructions array — the spec stage self-skips.
If it DOES, write a one-screen "## Spec" section into ${A.taskFilePath} containing: Contract
(signatures), Invariants, 3-7 observable Acceptance criteria, Error mapping (StaffeerError subclass),
and a pointer to the tests/contract/ suite. Use the ubiquitous language. Do NOT write any
implementation code.
${taskRef(A)}${RULES_CONTEXT}`,
    { label: 'spec:author', phase: 'spec', model: 'sonnet', effort: 'high', schema: { type: 'object', required: ['changesContract', 'spec'], properties: { changesContract: { type: 'boolean' }, spec: { type: 'object' }, filesTouched: { type: 'array', items: { type: 'string' } } } } }
  )
  if (!r || !r.changesContract) {
    return envelope('spec', [rec({ agentLabel: 'spec:author', model: 'sonnet', effort: 'high', atomicInstruction: 'Assess whether the slice changes a contract.', status: 'skipped', summary: 'No contract change; spec stage skipped.', filesTouched: (r && r.filesTouched) || [] })], { skipped: true }, null, 'decompose')
  }
  return envelope(
    'spec',
    [rec({ agentLabel: 'spec:author', model: 'sonnet', effort: 'high', atomicInstruction: 'Author the spec + contract-test outline for the slice.', status: 'ok', summary: 'Spec drafted; awaiting approval (SDD RULE-001).', filesTouched: r.filesTouched || [A.taskFilePath] })],
    { changesContract: true },
    { needsApproval: true, kind: 'spec', artifact: r.spec },
    'decompose'
  )
}

// === decompose =====================================================================================
if (stage === 'decompose') {
  const r = await agent(
    `Decompose this Staffeer slice into ORDERED ATOMIC INSTRUCTIONS. Rules: each instruction is ONE
coherent edit to ONE file (a single function/class/test). Tag complexityTag 'mechanical' (boilerplate:
value object, stub, trivial fn) or 'logic' (constraint/scorer/ranker/parser). Set dependsOn to the ids
this instruction needs first. Tie each to one acceptanceCriterion from the task file. Keep files cohesive
so same-file edits can be sequenced and cross-file edits parallelised.
${taskRef(A)}${specRef(A)}${RULES_CONTEXT}`,
    { label: 'decompose', phase: 'decompose', model: 'sonnet', effort: 'medium', schema: ATOMIC_SCHEMA }
  )
  const instructions = (r && r.instructions) || []
  return envelope(
    'decompose',
    [rec({ agentLabel: 'decompose', model: 'sonnet', effort: 'medium', atomicInstruction: 'Decompose the slice into atomic instructions.', status: instructions.length ? 'ok' : 'failed', summary: `${instructions.length} atomic instructions.` })],
    { atomicInstructions: instructions, count: instructions.length },
    null,
    'tests'
  )
}

// === tests (eval-first) ============================================================================
if (stage === 'tests') {
  const instructions = (A.prior && A.prior.atomicInstructions) || []
  const authored = await agent(
    `EVAL-FIRST. Before any implementation exists, author the executable spec for this slice:
1) deterministic golden-table SCENARIO EVALS under evals/ (include the mandatory NEGATIVE scenario,
   e.g. no-viable-match) — and remember a 100% relevance score is a coverage WARNING, never a pass;
2) contract/unit TESTS under tests/ for the atomic instructions below.
Then run them and confirm they FAIL (red) because the code does not exist yet. Report the failing run.
Atomic instructions:\n${JSON.stringify(instructions, null, 2)}\n${taskRef(A)}${specRef(A)}${RULES_CONTEXT}`,
    { label: 'tests:author', phase: 'tests', model: 'sonnet', effort: 'medium', schema: WORK_SCHEMA }
  )
  return envelope(
    'tests',
    [rec({ agentLabel: 'tests:author', model: 'sonnet', effort: 'medium', atomicInstruction: 'Author scenario evals + failing contract/unit tests; confirm red.', status: (authored && authored.status) || 'failed', summary: (authored && authored.summary) || '', filesTouched: (authored && authored.filesTouched) || [], verdict: { pass: (authored && authored.status === 'ok'), issues: (authored && authored.issues) || [] } })],
    { testsAuthored: true },
    null,
    'implement'
  )
}

// === implement (one agent per atomic instruction) ==================================================
if (stage === 'implement') {
  const instructions = (A.prior && A.prior.atomicInstructions) || []
  // Group by file: same file -> sequential (avoid write conflicts); different files -> parallel.
  const byFile = {}
  for (const ins of instructions) (byFile[ins.file] = byFile[ins.file] || []).push(ins)
  const fileGroups = Object.keys(byFile)

  const runOne = async (ins) => {
    const model = ins.complexityTag === 'mechanical' ? 'haiku' : 'sonnet'
    const effort = ins.complexityTag === 'mechanical' ? 'low' : 'medium'
    const res = await agent(
      `Perform EXACTLY ONE atomic edit. Do not touch anything outside this instruction.
File: ${ins.file}${ins.symbol ? ` (symbol: ${ins.symbol})` : ''}
Instruction: ${ins.instruction}
Acceptance criterion: ${ins.acceptanceCriterion}
Make the relevant failing test pass with the SIMPLEST code. Do not weaken or edit tests.${specRef(A)}${RULES_CONTEXT}`,
      { label: `impl:${ins.id}`, phase: 'implement', model, effort, schema: WORK_SCHEMA }
    )
    return rec({ agentLabel: `impl:${ins.id}`, model, effort, complexityTag: ins.complexityTag, atomicInstruction: ins.instruction, status: (res && res.status) || 'failed', summary: (res && res.summary) || '', filesTouched: (res && res.filesTouched) || [ins.file], verdict: { pass: !!(res && res.status === 'ok'), issues: (res && res.issues) || [] } })
  }

  const groupResults = await parallel(
    fileGroups.map((f) => async () => {
      const out = []
      const sorted = byFile[f].slice().sort((a, b) => (a.dependsOn || []).length - (b.dependsOn || []).length)
      for (const ins of sorted) out.push(await runOne(ins))   // sequential within a file
      return out
    })
  )
  const records = groupResults.filter(Boolean).flat()
  const allOk = records.length > 0 && records.every((x) => x.status === 'ok')
  return envelope('implement', records, { implemented: records.length, allOk }, null, 'quality')
}

// === quality gate (deterministic + bounded auto-repair) ============================================
if (stage === 'quality') {
  const records = []
  const runGate = () => agent(
    `Run the quality gate from the repo root: \`make format\` then \`make test\` then \`make lint\`.
Report pass=true only if all three succeed. On failure, capture the concrete failures (failing test
names, ruff/mypy errors) into "failures" and the tail of output into "output". Do not fix anything.`,
    { label: 'quality:gate', phase: 'quality', model: 'sonnet', effort: 'medium', schema: QUALITY_SCHEMA }
  )

  let result = await runGate()
  records.push(rec({ agentLabel: 'quality:gate', model: 'sonnet', effort: 'medium', atomicInstruction: 'Run make format/test/lint.', status: result && result.pass ? 'ok' : 'failed', summary: result ? (result.pass ? 'green' : `${(result.failures || []).length} failures`) : 'gate run failed', verdict: { pass: !!(result && result.pass), issues: (result && result.failures) || [] } }))

  let attempt = 0
  while (result && !result.pass && attempt < maxRepair) {
    attempt++
    const fix = await agent(
      `Bounded auto-repair (attempt ${attempt}/${maxRepair}). Fix ONLY what these failures report; the
SIMPLEST change that turns them green. Do not weaken tests or silence errors.
Failures:\n${JSON.stringify(result.failures || [], null, 2)}\nOutput tail:\n${result.output || ''}${RULES_CONTEXT}`,
      { label: `quality:repair#${attempt}`, phase: 'quality', model: 'sonnet', effort: 'medium', schema: WORK_SCHEMA }
    )
    records.push(rec({ agentLabel: `quality:repair#${attempt}`, model: 'sonnet', effort: 'medium', atomicInstruction: 'Repair quality-gate failures.', status: (fix && fix.status) || 'failed', attempts: attempt, summary: (fix && fix.summary) || '', filesTouched: (fix && fix.filesTouched) || [] }))
    result = await runGate()
    records.push(rec({ agentLabel: 'quality:gate', model: 'sonnet', effort: 'medium', atomicInstruction: 'Re-run make format/test/lint.', status: result && result.pass ? 'ok' : 'failed', attempts: attempt + 1, summary: result ? (result.pass ? 'green' : `${(result.failures || []).length} failures`) : 'gate run failed', verdict: { pass: !!(result && result.pass), issues: (result && result.failures) || [] } }))
  }

  if (!result || !result.pass) {
    return envelope('quality', records, { pass: false, repairs: attempt }, { needsApproval: true, kind: 'failure', artifact: { failures: (result && result.failures) || ['quality gate could not be run'] } }, 'verify')
  }
  return envelope('quality', records, { pass: true, repairs: attempt }, null, 'verify')
}

// === verify / review (adversarial, with bounded repair) ============================================
if (stage === 'verify') {
  const instructions = (A.prior && A.prior.atomicInstructions) || []
  const reviews = await parallel(
    instructions.map((ins) => async () => {
      const v = await agent(
        `Adversarially REVIEW this single change against its acceptance criterion and the binding rules.
Look for: silent drops/swallowed errors, functions > 20 lines, I/O leaking into the domain core,
missing negative-case handling, behaviour not matching the criterion. Default to pass=false if unsure.
File: ${ins.file}${ins.symbol ? ` (${ins.symbol})` : ''}\nInstruction: ${ins.instruction}\nCriterion: ${ins.acceptanceCriterion}${RULES_CONTEXT}`,
        { label: `verify:${ins.id}`, phase: 'verify', model: 'sonnet', effort: 'high', schema: VERDICT_SCHEMA }
      )
      return { ins, v: v || { pass: false, issues: ['review failed to run'] } }
    })
  )
  const records = []
  for (const { ins, v } of reviews.filter(Boolean)) {
    records.push(rec({ agentLabel: `verify:${ins.id}`, model: 'sonnet', effort: 'high', complexityTag: ins.complexityTag, atomicInstruction: `Review: ${ins.title}`, status: v.pass ? 'ok' : 'failed', summary: v.pass ? 'meets criterion' : `${v.issues.length} findings`, verdict: v }))
  }
  // Bounded repair for failed reviews.
  const failed = reviews.filter(Boolean).filter((x) => !x.v.pass)
  let attempt = 0
  if (failed.length && attempt < maxRepair) {
    attempt++
    const fixes = await parallel(
      failed.map(({ ins, v }) => async () => {
        const f = await agent(
          `Bounded auto-repair (attempt ${attempt}/${maxRepair}) for review findings on ${ins.file}.
Address ONLY these findings, simplest change, keep tests green:\n${JSON.stringify(v.issues, null, 2)}\nInstruction: ${ins.instruction}${RULES_CONTEXT}`,
          { label: `verify:repair:${ins.id}`, phase: 'verify', model: 'sonnet', effort: 'medium', schema: WORK_SCHEMA }
        )
        return rec({ agentLabel: `verify:repair:${ins.id}`, model: 'sonnet', effort: 'medium', atomicInstruction: `Repair review findings: ${ins.title}`, status: (f && f.status) || 'failed', attempts: attempt + 1, summary: (f && f.summary) || '', filesTouched: (f && f.filesTouched) || [ins.file] })
      })
    )
    records.push(...fixes.filter(Boolean))
  }
  const stillFailing = failed.length > 0 && attempt >= maxRepair
  return envelope('verify', records, { reviewed: reviews.length, repaired: attempt }, stillFailing ? { needsApproval: true, kind: 'failure', artifact: { findings: failed.map((x) => ({ id: x.ins.id, issues: x.v.issues })) } } : null, 'architecture')
}

// === architecture verification + ADR capture (gate) ================================================
if (stage === 'architecture') {
  const a = await agent(
    `Architecture review. Compare what this slice changed against .claude/principles/hexagonal-architecture.md,
the ports/adapters dependency rule, and the LikeC4 model in docs/architecture/*.c4. Classify:
- 'conformant'           : no architectural change, rules respected.
- 'unintended-deviation' : a rule was violated by accident (list deviations) — must be repaired.
- 'deliberate-change'    : the design intentionally changed (new port, new boundary, swapped adapter)
                           -> write a new ADR at docs/adr/NNN-<slug>.md (next free number; existing
                           highest is 002-agent-orchestration) using the Status/Context/Decision/
                           Consequences format of docs/adr/001-*.md, set adrPath/adrTitle, and set
                           likeC4ChangeNeeded if the .c4 model must be updated too.
${taskRef(A)}${RULES_CONTEXT}`,
    { label: 'architecture:verify', phase: 'architecture', model: 'sonnet', effort: 'high', schema: ARCH_SCHEMA }
  )
  const cls = (a && a.classification) || 'unintended-deviation'
  const records = [rec({ agentLabel: 'architecture:verify', model: 'sonnet', effort: 'high', atomicInstruction: 'Check architecture deviation; capture ADR if deliberate.', status: cls === 'unintended-deviation' ? 'failed' : 'ok', summary: `${cls}: ${(a && a.rationale) || ''}`, filesTouched: a && a.adrPath ? [a.adrPath] : [], verdict: { pass: cls !== 'unintended-deviation', issues: (a && a.deviations) || [] } })]

  if (cls === 'unintended-deviation') {
    let attempt = 0
    while (attempt < maxRepair) {
      attempt++
      const f = await agent(
        `Bounded auto-repair (attempt ${attempt}/${maxRepair}) for architecture deviations. Restore
conformance with the hexagonal rules; do not change behaviour. Deviations:\n${JSON.stringify((a && a.deviations) || [], null, 2)}${RULES_CONTEXT}`,
        { label: `architecture:repair#${attempt}`, phase: 'architecture', model: 'sonnet', effort: 'medium', schema: WORK_SCHEMA }
      )
      records.push(rec({ agentLabel: `architecture:repair#${attempt}`, model: 'sonnet', effort: 'medium', atomicInstruction: 'Repair architecture deviation.', status: (f && f.status) || 'failed', attempts: attempt, summary: (f && f.summary) || '', filesTouched: (f && f.filesTouched) || [] }))
      if (f && f.status === 'ok') break
    }
    return envelope('architecture', records, { classification: cls, repaired: true }, { needsApproval: true, kind: 'failure', artifact: { deviations: (a && a.deviations) || [] } }, 'report')
  }
  if (cls === 'deliberate-change') {
    return envelope('architecture', records, { classification: cls, adrPath: a.adrPath, likeC4ChangeNeeded: !!a.likeC4ChangeNeeded }, { needsApproval: true, kind: 'adr', artifact: { adrPath: a.adrPath, adrTitle: a.adrTitle, rationale: a.rationale, likeC4ChangeNeeded: !!a.likeC4ChangeNeeded } }, 'report')
  }
  return envelope('architecture', records, { classification: 'conformant' }, null, 'report')
}

// === progress report ===============================================================================
if (stage === 'report') {
  const r = await agent(
    `Update progress.html (the Staffeer build dashboard) to reflect this slice. Match the existing
markup/styles exactly: set this slice's badge (done/wip), its percentage, and tick its task list to
mirror the [x] state in ${A.taskFilePath}. Recompute the summary cards/overall bar if present. Do
not restyle or change unrelated slices.\n${taskRef(A)}`,
    { label: 'report:progress', phase: 'report', model: 'haiku', effort: 'low', schema: WORK_SCHEMA }
  )
  return envelope('report', [rec({ agentLabel: 'report:progress', model: 'haiku', effort: 'low', atomicInstruction: 'Update progress.html for this slice.', status: (r && r.status) || 'failed', summary: (r && r.summary) || '', filesTouched: (r && r.filesTouched) || ['progress.html'] })], { reported: true }, null, 'finalize')
}

// === finalize ======================================================================================
if (stage === 'finalize') {
  const r = await agent(
    `Finalize this slice. In ${A.taskFilePath}, mark the completed task items and the slice's
acceptance criteria from [~]/[ ] to [x] to reflect what is now implemented and green (do NOT mark
anything not actually done). Then propose a single Conventional Commit message (type(scope): subject,
imperative, < 72 chars; body explains why; "Refs: ${A.taskFilePath}") for the orchestrator to
commit. Do not run git yourself.\n${taskRef(A)}`,
    { label: 'finalize:checklist', phase: 'finalize', model: 'sonnet', effort: 'low', schema: { type: 'object', required: ['commitMessage', 'filesTouched'], properties: { commitMessage: { type: 'string' }, filesTouched: { type: 'array', items: { type: 'string' } } } } }
  )
  return envelope('finalize', [rec({ agentLabel: 'finalize:checklist', model: 'sonnet', effort: 'low', atomicInstruction: 'Mark task [x] and propose the commit message.', status: r ? 'ok' : 'failed', summary: (r && r.commitMessage) || '', filesTouched: (r && r.filesTouched) || [A.taskFilePath] })], { commitMessage: r && r.commitMessage }, { needsApproval: true, kind: 'commit', artifact: { commitMessage: r && r.commitMessage } }, null)
}

// === unknown stage =================================================================================
return envelope(stage || 'unknown', [], { error: `unknown stage: ${stage}` }, { needsApproval: true, kind: 'failure', artifact: { error: `unknown stage: ${stage}` } }, null)
