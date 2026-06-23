# Spec-Driven Development (SDD)

> **Intent**
> The **specification is the source of truth**, authored and approved *before* implementation.
> Code and tests are derived from the spec, not the other way round. In a hexagonal system the
> **port is the spec**: its signature, invariants, and error mapping form a contract that the
> domain core relies on and every adapter must satisfy. Freezing those contracts is exactly what
> lets the parallel tracks proceed without colliding — see `docs/tasks/parallelization-guide.md`.

This rule is authoritative for *how work is specified before it is built*. It complements
`docs/rules/task-execution.md` (the execution loop), `docs/rules/testing-principles.md`
(contract tests are preferable to mocking — RULE-202, §Decision Framework),
`docs/rules/hexagonal-architecture.md` (ports as contracts, §6 testing strategies), and the
team's build sequencing in `docs/tasks/00b-contracts.md` + `docs/tasks/parallelization-guide.md`.

---

## 1 Core principle

A unit of work (a port + its adapters, or a domain component) is not started until its **spec
exists and is approved**. The spec is the contract; the contract test is the spec made
executable; the implementation is whatever makes the contract test pass in the simplest way
(`docs/rules/clean-code.md`). This ordering — **spec → contract test → implementation** — is the
SDD loop, and it is how "eval-first" (README Principle 3) and TDD are realised at the unit level.

This dovetails with the build plan: the **C1/C2 contracts** (`docs/tasks/00b-contracts.md`) *are*
the specs that get frozen and approved, and that approval is the fan-out boundary after which
Tracks A–F run in parallel.

---

## 2 What a spec is

Each parallelizable unit carries a short, reviewable spec. For ports this lives next to the port
and is summarised in `00b-contracts.md`; for a domain component it lives in its slice file under
a `## Spec` heading. A spec states, and nothing more than:

- **Contract** — the port Protocol signature (typed params, return value objects) or, for a
  domain component, the pure-function signatures over domain models.
- **Invariants** — what must always hold (e.g. *no consultant is silently dropped*; *all
  LLM-bound text is PII-scrubbed*; *hard-constraint checks are deterministic and repeatable*; *an
  absent adapter contributes `ScoreContribution(value=0)`*; *the reasoner abstains rather than
  fabricates*).
- **Acceptance criteria** — observable, testable outcomes (mirrors the slice's criteria).
- **Error mapping** — which domain error (`StaffeerError` subclass) each failure surfaces; no
  silent failures (`docs/rules/code-quality.md`).
- **Inputs/outputs** — the domain value objects exchanged; never infrastructure types at the
  boundary (`docs/rules/hexagonal-architecture.md` §7.1).

A spec is *behavioural*, not an implementation plan. It says **what** and **why it must hold**,
never **how**.

---

## 3 Rules

### Must Have (Critical)

- **RULE-001:** No production code for a unit before its spec is written **and approved**
  (`docs/rules/task-execution.md` review gate). The spec, not the code, is reviewed first.
- **RULE-002:** Every port (`SupplyDemandSource`, `ProfileParser`, `FeedbackStore`,
  `SemanticIndex`, `LLMReasoner`, `PIIScrubber`) has a **contract-test suite** in
  `tests/contract/`, parametrised over an implementation, that asserts the port's behaviour
  against the spec. **Both the null-object adapter and every real adapter must pass that one
  suite** — it is the upgrade of the C1/C2 "null-object satisfiability test" into a full,
  reusable spec (`docs/tasks/00b-contracts.md`).
- **RULE-003:** The shared contracts — port Protocols, domain models/value objects, and the
  `ScoreContribution` / `ExplanationFactor` shapes — are frozen and approved in the **C1/C2
  contract waves before** Tracks A–F open (`docs/tasks/00b-contracts.md`,
  `parallelization-guide.md`). Changing a frozen contract after fan-out requires a spec amendment
  and re-approval (RULE-001), because other tracks depend on it.
- **RULE-004:** When implementation reveals the spec was wrong, **stop and amend the spec
  first**, then the contract test, then the code. Never let code silently diverge from its spec.
  Prefer non-breaking change: adding a defaulted optional field, or a new named
  `ScoreContribution`/`ExplanationFactor`, never reshaping a frozen record.

### Should Have (Important)

- **RULE-101:** Keep specs minimal — a contract, invariants, acceptance criteria, error mapping.
  If a spec needs more than a screen, the unit is too big; decompose with `/breakdown`.
- **RULE-102:** Prefer **contract tests over mocks**. A null-object (or fake) adapter that
  satisfies the contract suite is a legitimate test double for integration; ad-hoc mocks of
  domain logic are not (`docs/rules/testing-principles.md` RULE-102).
- **RULE-103:** Specs are versioned with the code and referenced from the slice file
  (`Refs: docs/tasks/...`). A PR that changes a contract shows the spec diff.

### Could Have (Preferred)

- **RULE-201:** Use `/specify` to author a new spec and `/clarify` to refine an ambiguous one
  before writing it down.
- **RULE-202:** Where a contract is exercised by the LLM path, the spec names the relevant eval
  (`evals/`) so quality is measured against the spec, not string equality.

---

## 4 How SDD enables parallelism

Once C1/C2 have frozen **all** port Protocols, domain models/value objects, the
`ScoreContribution`/`ExplanationFactor` shapes, and their `tests/contract/` suites, each adapter
and each domain component becomes an independent track: it is built against a *frozen contract*,
verified by the *contract suite*, merged behind its *null object*, and never needs to see another
track's code. Integration slices (I1–I7) then swap a null object for a real adapter against a
contract already proven green. The full track/slice map and per-PR Definition of Done live in
`docs/tasks/parallelization-guide.md`.

---

## TL;DR

1. **Spec before code** — the spec (the port contract) is the source of truth and is reviewed first.
2. **Contract test = executable spec** — in `tests/contract/`, one suite per port; the null object
   and every real adapter must pass it.
3. **Freeze contracts in C1/C2** — that frozen set is the fan-out boundary that unlocks Tracks A–F.
4. **Spec wrong? Amend the spec first**, then the test, then the code — never diverge silently;
   prefer additive (defaulted field, new `ScoreContribution`) over reshaping a frozen record.
