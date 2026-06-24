---
allowed-tools: AskUserQuestion, Read, Write, TodoWrite
argument-hint: "[port or component to specify]"
description: Author a reviewable spec (contract, invariants, acceptance criteria, error mapping) before any implementation, per Spec-Driven Development
---

## Spec Authoring Workshop

Turn a well-defined work item into a **reviewable specification** that becomes the source of
truth for implementation. This is the first step of the **Spec-Driven Development (SDD)** loop:
**spec → contract test → implementation** (see "SDD foundations" at the foot of this file). Use
this *after* `/clarify` (idea is crisp) and `/breakdown` (work item is appropriately sized), and
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
- Amending a contract that turned out to be wrong (SDD foundations, Rule 4 below).

## Process

### Step 1: Establish context

Read the relevant docs so the spec is grounded, not invented:
- The owning task file in `docs/tasks/` (acceptance criteria, dependencies).
- `docs/conventions.md` (directory structure, naming, error/logging) and
  `.claude/principles/hexagonal-architecture.md` (ports as contracts, error mapping at boundaries).
- `.claude/principles/domain-driven-design.md` for the ubiquitous language (beach, roll-off, new
  joiner, co-location, Chennai-open).

### Step 2: Draft the contract

Capture, using AskUserQuestion only where genuinely ambiguous:
- **Signature** — the Protocol methods (typed params, return value objects) or pure-function
  signatures. Domain types only at the boundary; never infrastructure types.
- **Invariants** — what must always hold (no silent drops; PII scrubbed before the LLM;
  determinism where required; explanations always present).
- **Acceptance criteria** — observable, testable outcomes (3-7, mirroring the task file).
- **Error mapping** — the `StaffeerError` subclass each failure surfaces (no silent failures,
  `.claude/principles/code-quality.md`).
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
executable (SDD foundations, Rule 2 below). List the behaviours it asserts, including **negative
scenarios** (`.claude/principles/testing-principles.md`). The port's **null-object adapter and
every real adapter must pass this one suite** — it is the upgrade of the C1/C2 null-object
satisfiability test into a full spec (`docs/tasks/00b-contracts.md`).

### Step 5: Request approval

Present the spec for review. **Do not start implementation until the spec is approved** (SDD
foundations, Rule 1 below; the review gate in CLAUDE.md → Development workflow). On approval the
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
- ❌ Change a frozen contract silently — amend the spec and re-approve (SDD foundations, Rule 4).

## Workflow Summary

1. **Context**: read the task file and the binding rules.
2. **Contract**: signature, invariants, acceptance criteria, error mapping.
3. **Write**: spec into the unit's task file / port stub.
4. **Contract test**: specify the executable spec in `tests/contract/`.
5. **Approve**: review and approve before any implementation; the frozen contract unlocks parallel work.

## SDD foundations (binding)

The specification is the **source of truth**, authored and approved *before* implementation; code
and tests are derived from the spec, not the other way round. In a hexagonal system the **port is
the spec**: its signature, invariants, and error mapping form a contract the domain core relies on
and every adapter must satisfy. Freezing those contracts in the **C1/C2 contract waves**
(`docs/tasks/00b-contracts.md`) is the fan-out boundary that lets Tracks A–F run in parallel
(`docs/tasks/parallelization-guide.md`).

A spec is **behavioural** — it states *what* must hold and *why*, never *how*: a contract
(signature), invariants, acceptance criteria, error mapping, and the domain value objects
exchanged. Keep it to one screen; if it sprawls, the unit is too big (`/breakdown` it).

Binding rules:

1. **No production code before the spec is written and approved.** The spec, not the code, is
   reviewed first (CLAUDE.md → Development workflow review gate).
2. **Every port has a contract-test suite in `tests/contract/`**, parametrised over an
   implementation, asserting the port's behaviour against the spec. The null-object adapter and
   every real adapter must pass that one suite. Prefer **contract tests over mocks** — a
   null-object/fake that satisfies the suite is a legitimate integration double; ad-hoc mocks of
   domain logic are not (`.claude/principles/testing-principles.md`).
3. **Shared contracts are frozen and approved in C1/C2 before the tracks open.** Changing a frozen
   contract after fan-out requires a spec amendment and re-approval (Rule 1), because other tracks
   depend on it.
4. **Spec wrong? Amend the spec first**, then the contract test, then the code — never let code
   silently diverge. Prefer additive change (a defaulted optional field, a new named
   `ScoreContribution`/`ExplanationFactor`) over reshaping a frozen record.
