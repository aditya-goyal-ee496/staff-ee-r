# Slice C — Contracts (the parallelism keystone)

**Goal:** freeze the **ports, domain models/value objects, null-object adapters, and the
composition root** so that — in a ports-and-adapters system — every track can build adapters
and domain logic *in parallel* against a stable surface without colliding in shared files.
This is the second (and last) irreducible serial step; once it merges, the work fans out.

**Type:** Task (technical) · **Priority:** P0 · **Depends on:** S0 ([`00a-ci-baseline.md`](00a-ci-baseline.md)) ·
**Parallelization:** the fan-out boundary — Tracks A/B/C/F open the moment **C1** merges; D/E
open after **C2**. See [`parallelization-guide.md`](parallelization-guide.md).

> The two anti-serialization design rules below are load-bearing. Without them, four tracks
> would edit one `scoring.py` formula and one `Explanation` record — re-creating the
> serialization this whole restructure removes.

## C1 — Contracts wave 1 (well-understood surface)

**Depends on:** S0. Merge this before opening Tracks A/B/C/F.

### Acceptance criteria

- [ ] Frozen Pydantic models import with **no I/O** (dependency rule holds).
- [ ] Every port is a `Protocol` with a matching **null-object** adapter that satisfies it.
- [ ] `build_matcher(config) -> Matcher` and `Matcher.match(role) -> Shortlist` exist and run
      end-to-end returning an empty/inert result (all ports default to their null object).
- [ ] One test per null object proves the Protocol is satisfiable; `make test`/`lint` green.

### Tasks

- [ ] **Models / value objects** (`domain/models.py`) — `SupplyState`, `Priority` enums;
      `Consultant`, `Role` (frozen Pydantic). **Pre-bake all known optional fields with safe
      defaults now** so later additions are never breaking: `Consultant.available_from`,
      `confidence`, `skills_verified`, provenance. Plus `ConstraintCheck(name, passed, reason)`,
      `EligibilityResult(consultant, checks)`, `SkillScore`, **`ScoreContribution(source,
      value, weight, detail)`**, `Explanation` / **`ExplanationFactor`**, `Shortlist`. Skills
      as `list[str]`; dates as `date`. Ubiquitous language from the brief.
- [ ] **Ports understood today** (`ports/`) — `SupplyDemandSource` (`open_roles()`,
      `role(id)`, `consultants(*states)`); `ProfileParser.parse(path) -> ParsedProfile`;
      `FeedbackStore.for_consultant(id) -> Feedback`; `PIIScrubber.scrub(text) -> ScrubbedText`.
- [ ] **Null-object adapters** (`adapters/`) — `NullProfileParser`, `NullFeedbackStore`,
      `NullPIIScrubber`, plus an empty in-memory `SupplyDemandSource` for tests.
- [ ] **Composition root** — `build_matcher(config) -> Matcher`, defaulting every port to its
      null object; `Matcher.match(role) -> Shortlist`. **Fail closed:** if an LLM/semantic
      path is later wired without a real `PIIScrubber`, `build_matcher` raises.
- [ ] **Tests** — one satisfiability test per null object; one test that `build_matcher` with
      all-null ports returns an empty `Shortlist` without error.

> If this PR exceeds the <30-min review rule, split it **models PR → ports/root PR** the same
> day (still one serial step in practice).

## C2 — Contracts wave 2 (domain-informed ports, small, deferred ~2-3 days)

**Depends on:** C1 + Track-A's first PRs (so `Evidence`/`Hit`/`SoftAssessment` shapes are
informed by the real scoring core). Lands while Track A is mid-flight — serializes nobody.

### Acceptance criteria

- [ ] `SemanticIndex` and `LLMReasoner` ports frozen with null objects that compose inertly.
- [ ] `make test`/`lint` green; Tracks D and E can now open.

### Tasks

- [ ] **`SemanticIndex` port** (`ports/`) — `upsert(items)`, `query(text, k) -> [Hit]`; define
      the `Hit` shape. `NullSemanticIndex.query` → `[]` (→ `ScoreContribution(value=0)`).
- [ ] **`LLMReasoner` port** (`ports/`) — `assess(role, candidate, evidence) -> SoftAssessment`
      (score + rationale + cited sources); define `Evidence` + `SoftAssessment`.
      `NullLLMReasoner` → **abstains** (zero contribution, no fabrication).

## The two anti-serialization rules (also in `parallelization-guide.md`)

- **Scoring is a sum of named `ScoreContribution`s, not a monolithic formula.** Lexical (03),
  semantic (05), soft-LLM (06), and provenance (08) tracks each *append a contributor* —
  nobody edits a shared formula. An absent adapter contributes `value=0`, so the blend is
  always valid.
- **`Explanation` is an open list of `ExplanationFactor`s, not a fixed-field record.** Every
  factor that moved the rank is appended (satisfies Principle 1 with zero merge contention).

## Notes

- This is *interfaces + dataclasses + no-op bodies* — designed to read fast and freeze cleanly.
- Adding a defaulted optional field is the only non-breaking model change; design so that is
  the only kind ever needed downstream.
- Definition of Done: see [`parallelization-guide.md`](parallelization-guide.md).
