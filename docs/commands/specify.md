---
allowed-tools: AskUserQuestion, Read, Write, TodoWrite
argument-hint: "[port or component to specify]"
description: Author a reviewable spec (contract, invariants, acceptance criteria, error mapping) before any implementation, per Spec-Driven Development
---

## Spec Authoring Workshop

Turn a well-defined work item into a **reviewable specification** that becomes the source of
truth for implementation. This is the first step of the SDD loop in
`docs/rules/spec-driven-development.md`: **spec → contract test → implementation**. Use this
*after* `/clarify` (idea is crisp) and `/breakdown` (work item is appropriately sized), and
*before* writing any production code.

## Usage

/specify [name of the port or domain component to specify]

If no target is given, ask what is being specified. A spec covers exactly one parallelizable
unit: one port + its contract, or one domain component (pure function group over domain models).

## When to use

- Authoring a new **port** in the **C1/C2 contract waves** (`docs/tasks/00b-contracts.md`):
  `SupplyDemandSource`, `ProfileParser`, `FeedbackStore`, `SemanticIndex`, `LLMReasoner`,
  `PIIScrubber` — the spec *is* the frozen contract Tracks A–F build against.
- Specifying a **domain component** (constraint filter, scorer, ranker, explainer) or a shared
  shape (`ScoreContribution`, `ExplanationFactor`) before implementation.
- Amending a contract that turned out to be wrong (`spec-driven-development.md` RULE-004).

## Process

### Step 1: Establish context

Read the relevant docs so the spec is grounded, not invented:
- The owning task file in `docs/tasks/` (acceptance criteria, dependencies).
- `docs/conventions.md` (directory structure, naming, error/logging) and
  `docs/rules/hexagonal-architecture.md` (ports as contracts, error mapping at boundaries).
- `docs/rules/domain-driven-design.md` for the ubiquitous language (beach, roll-off, new
  joiner, co-location, Chennai-open).

### Step 2: Draft the contract

Capture, using AskUserQuestion only where genuinely ambiguous:
- **Signature** — the Protocol methods (typed params, return value objects) or pure-function
  signatures. Domain types only at the boundary; never infrastructure types.
- **Invariants** — what must always hold (no silent drops; PII scrubbed before the LLM;
  determinism where required; explanations always present).
- **Acceptance criteria** — observable, testable outcomes (3-7, mirroring the task file).
- **Error mapping** — the `StaffeerError` subclass each failure surfaces (no silent failures).
- **Inputs/outputs** — the domain value objects exchanged.

### Step 3: Write the spec

Write the spec into the unit's location:
- For a **port**: a `## Spec` section in the owning slice file, plus the Protocol stub frozen in
  the C1/C2 contract wave (`docs/tasks/00b-contracts.md`).
- For a **domain component**: a `## Spec` section in its slice file (e.g. `02-beach-matching.md`).

```markdown
## Spec — <unit name>

**Contract**
\`\`\`python
class SemanticIndex(Protocol):
    def upsert(self, items: list[IndexItem]) -> None: ...
    def query(self, text: str, k: int) -> list[Hit]: ...
\`\`\`

**Invariants**
- <must-always-hold statement>

**Acceptance criteria**
- [ ] <observable, testable outcome>

**Error mapping**
- <infrastructure failure> -> <StaffeerError subclass>

**Contract test:** `tests/contract/test_<port>.py` — every adapter must pass it.
```

### Step 4: Define the contract test

Specify (do not yet implement) the contract-test suite in `tests/contract/` that makes the spec
executable (`docs/rules/spec-driven-development.md` RULE-002). List the behaviours it asserts,
including **negative scenarios** (`docs/rules/testing-principles.md` RULE-104). The port's
**null-object adapter and every real adapter must pass this one suite** — it is the upgrade of
the C1/C2 null-object satisfiability test into a full spec (`docs/tasks/00b-contracts.md`).

### Step 5: Request approval

Present the spec for review. **Do not start implementation until the spec is approved**
(`spec-driven-development.md` RULE-001; `task-execution.md` review gate). On approval the
contract is frozen — and, per `docs/tasks/parallelization-guide.md`, the track that owns it can
proceed in parallel with its peers behind the null-object default.

## Guidelines

### DO
- ✅ Keep the spec to a contract + invariants + acceptance criteria + error mapping (one screen).
- ✅ State behaviour (what/why), never implementation (how).
- ✅ Name the negative scenarios the contract test must cover.
- ✅ Use the ubiquitous language from the brief.

### DON'T
- ❌ Write code before the spec is approved.
- ❌ Put infrastructure types in a contract signature.
- ❌ Let a spec sprawl — that signals the unit is too big (`/breakdown` it).
- ❌ Change a frozen contract silently — amend the spec and re-approve (RULE-004).

## Workflow Summary

1. **Context**: read the task file and the binding rules.
2. **Contract**: signature, invariants, acceptance criteria, error mapping.
3. **Write**: spec into the unit's task file / port stub.
4. **Contract test**: specify the executable spec in `tests/contract/`.
5. **Approve**: review and approve before any implementation; the frozen contract unlocks parallel work.
