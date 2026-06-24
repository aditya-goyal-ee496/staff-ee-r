# Slice C — Contracts (the parallelism keystone)

**Goal:** freeze the **ports, domain models/value objects, null-object adapters, the
composition root, and a contract-test suite per port** so that — in a ports-and-adapters system —
every track can build adapters and domain logic *in parallel* against a stable surface without
colliding in shared files. This is the second (and last) irreducible serial step; once it merges,
the work fans out. These frozen contracts **are the specs** (`.claude/commands/specify.md`)
that every track is reviewed against before implementation.

**Type:** Task (technical) · **Priority:** P0 · **Depends on:** S0 ([`00a-ci-baseline.md`](00a-ci-baseline.md)) ·
**Parallelization:** the fan-out boundary — Tracks A/B/C/F open the moment **C1** merges; D/E
open after **C2**. See [`parallelization-guide.md`](parallelization-guide.md).

> The two anti-serialization design rules below are load-bearing. Without them, four tracks
> would edit one `scoring.py` formula and one `Explanation` record — re-creating the
> serialization this whole restructure removes.

## C1 — Contracts wave 1 (well-understood surface)

**Depends on:** S0. Merge this before opening Tracks A/B/C/F.

### Acceptance criteria

- [x] Frozen Pydantic models import with **no I/O** (dependency rule holds).
- [x] Every port is a `Protocol` with a matching **null-object** adapter that satisfies it.
- [x] `build_matcher(config) -> Matcher` and `Matcher.match(role) -> Shortlist` exist and run
      end-to-end returning an empty/inert result (all ports default to their null object).
- [x] A **contract-test suite per port** in `tests/contract/`, parametrised over an
      implementation; the null object passes it now and every real adapter (Tracks B–E) reuses it
      unchanged (`.claude/commands/specify.md` (SDD foundations, Rule 2)). `make test`/`lint` green.

### Tasks

- [x] **Models / value objects** (`domain/models.py`) — `SupplyState`, `Priority` enums;
      `Consultant`, `Role` (frozen Pydantic). **Pre-bake all known optional fields with safe
      defaults now** so later additions are never breaking: `Consultant.available_from`,
      `confidence`, `skills_verified`, provenance. Plus `ConstraintCheck(name, passed, reason)`,
      `EligibilityResult(consultant, checks)`, `SkillScore`, **`ScoreContribution(source,
      value, weight, detail)`**, `Explanation` / **`ExplanationFactor`**, `Shortlist`. Skills
      as `list[str]`; dates as `date`. Ubiquitous language from the brief.
- [x] **Ports understood today** (`ports/`) — `SupplyDemandSource` (`open_roles()`,
      `role(id)`, `consultants(*states)`); `ProfileParser.parse(path) -> ParsedProfile`;
      `FeedbackStore.for_consultant(id) -> Feedback`; `PIIScrubber.scrub(text) -> ScrubbedText`.
- [x] **Null-object adapters** (`adapters/`) — `NullProfileParser`, `NullFeedbackStore`,
      `NullPIIScrubber`, plus an empty in-memory `SupplyDemandSource` for tests.
- [x] **Composition root** — `build_matcher(config) -> Matcher`, defaulting every port to its
      null object; `Matcher.match(role) -> Shortlist`. **Fail closed:** if an LLM/semantic
      path is later wired without a real `PIIScrubber`, `build_matcher` raises.
- [x] **Contract suites** (`tests/contract/`) — one per port (`test_supply_demand.py`,
      `test_profiles.py`, `test_feedback.py`, `test_pii.py`), parametrised over an implementation
      fixture and asserting the spec's behaviour **including negative scenarios** (malformed input
      → mapped `StaffeerError`, empty results). The null object is the first implementation to
      pass each suite; real adapters reuse the same suite. Plus one test that `build_matcher`
      with all-null ports returns an empty `Shortlist` without error.

> If this PR exceeds the <30-min review rule, split it **models PR → ports/root PR** the same
> day (still one serial step in practice).

## C2 — Contracts wave 2 (domain-informed ports, small, deferred ~2-3 days)

**Depends on:** C1 + Track-A's first PRs (so `Evidence`/`Hit`/`SoftAssessment` shapes are
informed by the real scoring core). Lands while Track A is mid-flight — serializes nobody.

### Acceptance criteria

- [x] `SemanticIndex` and `LLMReasoner` ports frozen with null objects that compose inertly.
- [x] A contract-test suite per port (`tests/contract/test_semantic_index.py`,
      `test_reasoner.py`) — the LLM suite runs against a no-network **stub** reasoner — passed by
      the null object; Tracks D/E reuse it.
- [x] `make test`/`lint` green; Tracks D and E can now open.

### Tasks

- [x] **`SemanticIndex` port** (`ports/`) — `upsert(items)`, `query(text, k) -> [Hit]`; define
      the `Hit` shape. `NullSemanticIndex.query` → `[]` (→ `ScoreContribution(value=0)`).
- [x] **`LLMReasoner` port** (`ports/`) — `assess(role, candidate, evidence) -> SoftAssessment`
      (score + rationale + cited sources); define `Evidence` + `SoftAssessment`.
      `NullLLMReasoner` → **abstains** (zero contribution, no fabrication).

## Spec — SemanticIndex port (C2)

**Contract**
```python
from typing import Protocol, runtime_checkable
from staffeer.domain.models import ValueObject

class IndexItem(ValueObject):
    """One unit of content to index (a scrubbed skill summary or profile excerpt)."""
    id: str           # stable, unique key (consultant id + slice tag)
    text: str         # PII-scrubbed text to embed
    metadata: dict[str, str] = {}   # opaque pass-through (location, state, grade …)

class Hit(ValueObject):
    """One result returned by a semantic query."""
    id: str           # matches IndexItem.id
    score: float      # cosine similarity in [0.0, 1.0]
    text: str         # the stored text that was matched
    metadata: dict[str, str] = {}

@runtime_checkable
class SemanticIndex(Protocol):
    def upsert(self, items: list[IndexItem]) -> None:
        """Persist or update `items`; idempotent on `id`."""
        ...
    def query(self, text: str, k: int) -> list[Hit]:
        """Return up to `k` nearest neighbours for `text`; empty list when index is empty."""
        ...
```

**Invariants**
- `query` never raises on an empty index; it returns `[]`.
- `query` never returns more than `k` results.
- `Hit.score` is in `[0.0, 1.0]`.
- `upsert` is idempotent: calling it twice with the same `id` updates the stored entry, no duplicate.
- Text reaching `upsert` must already be PII-scrubbed (the caller's responsibility, enforced by `build_matcher` wiring — `PIIScrubber` is required when a real `SemanticIndex` is wired).
- `NullSemanticIndex.query` always returns `[]`, yielding `ScoreContribution(value=0)` downstream.

**Acceptance criteria**
- [x] `NullSemanticIndex` passes `tests/contract/test_semantic_index.py` without network I/O.
- [x] `query` on an empty `NullSemanticIndex` returns `[]`, not `None`.
- [x] `upsert` followed by `query` on a real adapter returns at least one `Hit` with `score` in `[0.0, 1.0]`.
- [x] `Hit.id` returned by `query` matches an `IndexItem.id` previously passed to `upsert`.
- [x] `query` with `k=1` returns at most one result.
- [x] `IndexItem` with a duplicate `id` can be upserted without error (idempotency).
- [x] Malformed `text` (empty string) to `upsert` is accepted without raising.

**Error mapping**
- Backing-store unavailable during `upsert` → `SemanticIndexError(StaffeerError)`
- Backing-store unavailable during `query` → `SemanticIndexError(StaffeerError)`

**Contract test:** `tests/contract/test_semantic_index.py` — parametrised over `NullSemanticIndex`; Track D's Milvus adapter reuses the same suite.

---

## Spec — LLMReasoner port (C2)

**Contract**
```python
from typing import Protocol, runtime_checkable
from staffeer.domain.models import Consultant, Role, ValueObject

class Evidence(ValueObject):
    """Structured, PII-scrubbed inputs the reasoner may draw on to justify a match."""
    skill_score: float          # deterministic coverage from Track A (0..1)
    semantic_hits: tuple[str, ...] = ()   # top semantic hit texts from SemanticIndex
    feedback_notes: tuple[str, ...] = ()  # scrubbed feedback snippets
    provenance: str = ""        # supply-state context (beach / roll-off / new joiner)

class SoftAssessment(ValueObject):
    """One LLM-produced soft judgement for a (role, consultant) pair."""
    score: float                # 0.0 (abstain / no signal) to 1.0 (strong fit)
    rationale: str              # human-readable; MUST reference cited_sources
    cited_sources: tuple[str, ...] = ()   # which Evidence fields influenced the reasoning
    abstained: bool = False     # True when the reasoner produced no signal (null or failure)

@runtime_checkable
class LLMReasoner(Protocol):
    def assess(self, role: Role, candidate: Consultant, evidence: Evidence) -> SoftAssessment:
        """Return a soft assessment; abstain (score=0, abstained=True) rather than fabricate."""
        ...
```

**Invariants**
- `NullLLMReasoner.assess` always returns `SoftAssessment(score=0.0, rationale="", abstained=True)` — zero contribution, no fabrication.
- `SoftAssessment.score` is in `[0.0, 1.0]`.
- A real reasoner must never receive un-scrubbed PII; `Evidence` fields are scrubbed before construction (caller's responsibility, enforced by `build_matcher` wiring).
- When `abstained=True`, `cited_sources` must be empty and `score` must be `0.0`.
- A non-abstaining `SoftAssessment` (`abstained=False`) must have a non-empty `rationale`.

**Acceptance criteria**
- [x] `NullLLMReasoner` passes `tests/contract/test_reasoner.py` with no network I/O.
- [x] `NullLLMReasoner.assess` returns `SoftAssessment(score=0.0, abstained=True)`.
- [x] A stub reasoner (no-network) in the contract suite returns a `SoftAssessment` with `score` in `[0.0, 1.0]`.
- [x] An abstaining response has empty `cited_sources` and `score == 0.0`.
- [x] A non-abstaining response has a non-empty `rationale`.
- [x] `SoftAssessment` is a `ValueObject` (frozen, equality-by-value) and carries no infrastructure types.
- [x] `build_matcher` with a real `LLMReasoner` wired but no real `PIIScrubber` raises at construction time (fail-closed).

**Error mapping**
- LLM provider unreachable or timeout → `LLMReasonerError(StaffeerError)` (adapter maps; domain never sees HTTP errors)
- LLM returns malformed or unparseable output → `LLMReasonerError(StaffeerError)`

**Contract test:** `tests/contract/test_reasoner.py` — runs against `NullLLMReasoner` and a `StubLLMReasoner` (hard-coded deterministic response, no network); Track E's DSPy adapter reuses the same suite.

---

## The two anti-serialization rules (also in `parallelization-guide.md`)

- **Scoring is a sum of named `ScoreContribution`s, not a monolithic formula.** Lexical (03),
  semantic (05), soft-LLM (06), and provenance (08) tracks each *append a contributor* —
  nobody edits a shared formula. An absent adapter contributes `value=0`, so the blend is
  always valid.
- **`Explanation` is an open list of `ExplanationFactor`s, not a fixed-field record.** Every
  factor that moved the rank is appended (satisfies Principle 1 with zero merge contention).

## Notes

- This is *interfaces + dataclasses + no-op bodies + contract suites* — designed to read fast
  and freeze cleanly. The contract suites are the **executable spec** each port is reviewed and
  approved against before any track implements it (`.claude/commands/specify.md`).
- Adding a defaulted optional field is the only non-breaking model change; design so that is
  the only kind ever needed downstream.
- Definition of Done: see [`parallelization-guide.md`](parallelization-guide.md).
