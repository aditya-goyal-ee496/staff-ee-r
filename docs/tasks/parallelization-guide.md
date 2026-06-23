# Parallelization guide — how the team works this plan

Read this first. It explains how Staffeer's build is sequenced so **2–3 developers** can work
concurrently, every PR is atomically testable, CI gates from the first commit, and `main`
stays deployable. It complements [`00-build-plan.md`](00-build-plan.md) (the slice index) and
the rule files in `docs/rules/`.

## The shape: bootstrap → contracts → fan-out → integration

The original 9 vertical slices were chained serially because they edit the same files
(`domain/models.py`, `domain/scoring.py`, `cli/main.py`), **not** because of real data
dependencies. Once the *ports + models* are frozen, that false serialization disappears and
the work fans out.

```
S0  CI baseline ──► C1 Contracts (wave 1) ──► [fan-out: Tracks A, B, C, F]
   (00a)             (00b)                └──► C2 Contracts (wave 2) ──► [Tracks D, E]

Integration wiring (thin PRs; each = one null→real swap or one flag):
  I1 Beach e2e ─► I2 Skill scoring ─► I3 Semantic blend ┐
                                   └─► I4 LLM soft score ┴─► I5 Supply expansion
                                                          ├─► I6 Relevance evals
                                                          └─► I7 Optional
```

**Irreducible critical path** (the only true serial part): `S0 → C1`. After C1, everything
fans out. The shortest path to a *shippable beach matcher* is
`S0 → C1 → (A-matching ‖ B-xlsx) → I1` — **four hops, not seven.**

## Tracks (parallel after contracts) — coarse, for 2–3 devs

| Track | Scope (grouped into ~1–2 PRs) | Opens after | Maps to old slice |
|---|---|---|---|
| **A — Domain core** | `eligibility.py` (location + availability), `skills.py` (normalize + adjacency), `scoring.py` (lexical contributor + contribution-sum), `ranking.py`, `explain.py`. Pure, no I/O. | C1 | 02, 03 |
| **B — Data adapters** | `xlsx_supply_demand.py`, `docling_profiles.py`, `markdown_feedback.py` (one owner). | C1 | 01, 04 |
| **C — Security/PII** | `presidio_pii.py` + security negative test. | C1 | 04 |
| **D — Semantic adapter** | `milvus_index.py` round-trip + embedding choice (ADR). | C2 | 05 |
| **E — LLM reasoner** | `dspy_openrouter.py`, free-text role parse, soft-score contributor, abstention. | C2 | 06 |
| **F — Eval scaffolding** | `evals/` deterministic golden-table harness + `README.md`; Promptfoo/DeepEval skeleton; **heavy-lane** `integration.yml`. | C1 | 02, 07 |

## Integration slices (thin wiring PRs; each keeps main green)

Each swaps a null object for a real adapter in `build_matcher` and/or flips a config flag.

| Slice | Wires | Depends on |
|---|---|---|
| **I1** Beach matching e2e | real xlsx + matching; CLI `roles` / `match ROLE_ID [--show-excluded]` | A-matching, B-xlsx |
| **I2** Skill scoring in CLI | scoring/ranking/explain contributors | I1, A-scoring |
| **I3** Semantic blend | `Null→Milvus`; semantic contributor; `make index`; `--semantic` | I2, D, C |
| **I4** LLM soft score + free-text role | `Null→Dspy`; soft contributor; LLM logging | I2, E, C |
| **I5** Supply expansion | `--include rolling_off,new_joiner`; provenance weighting | I1 + (I2 or I4) |
| **I6** Relevance evals | DeepEval + Promptfoo, LLM-as-judge | I4, F |
| **I7** Optional | multi-role/team, web UI, persistence, observability | I4 |

**I3 ‖ I4** are order-free (additive contributors). I5/I6/I7 only depend on I4.

## The four rules that keep parallel work from colliding

1. **Scoring is a sum of named `ScoreContribution`s, not a monolithic formula.** Each track
   *appends a contributor*; nobody edits a shared formula. An absent adapter contributes
   `value=0`, so the blend is always valid. (Defined in [`00b-contracts.md`](00b-contracts.md).)
2. **`Explanation` is an open list of `ExplanationFactor`s.** Every factor that moved the
   rank is appended — satisfies Principle 1 ("surface every factor") with zero contention.
3. **Null-object = "not built/wired"; runtime flag = "built but optional/costly."** Never
   flag-gate the domain core. A half-built `SemanticIndex` is a `NullSemanticIndex` (the
   default wiring, returns no hits), not a flag a user could flip into a crash.
4. **One composition root** `build_matcher(config) -> Matcher`. Tracks wire adapters via
   `config.py` selection, never into the CLI body. `cli/main.py` changes ~twice total
   (scaffold at I1, free-text role at I4). **Fail closed on PII:** an active LLM/semantic
   path with no real `PIIScrubber` makes `build_matcher` raise.

## Adapter selection / config (no flag framework)

Extend `config.py` into a frozen `StaffeerConfig` from env (12-factor): `data_path`,
`openrouter_api_key`, plus capability selectors `semantic_enabled=False`, `llm_enabled=False`,
`include_states=[BEACH]`, and the per-contributor `weights`. `build_matcher(config)` picks
real-vs-null per port; CLI flags are thin overrides merged into config, not a parallel path.

## CI gates — two lanes (cost-aware)

- **Fast lane (`ci.yml`)** — every PR + push to `main`; hermetic (no secrets/network/heavy
  models). `make lint` (ruff format-check + ruff check + **mypy strict**) + `make test`
  (unit + fixture-integration + **deterministic scenario evals, 100% green required**).
  LLM/semantic appear only via stubs/null objects; real-data/key tests are `skipif`-gated.
  **Gates merge (`git-rules.md` RULE-006).**
- **Heavy lane (`integration.yml`)** — nightly + on `run-heavy` label + manual dispatch; has
  secrets. Optional dep groups + spaCy model; real-data integration, Milvus round-trip, full
  `make eval` incl. DeepEval/Promptfoo relevance (LLM-as-judge). Path-/label-filtered to PRs
  touching prompts/weights/scoring/evals/adapters. **A relevance suite scoring 100% emits a
  coverage-review warning — never a pass** (ADR-001).

## Spec-driven + TDD + eval-first (how every task is built)

- **Spec-first** (`docs/rules/spec-driven-development.md`). The port contract (frozen in C1/C2)
  is the **spec**, reviewed and approved *before* implementation; the `tests/contract/` suite is
  that spec made executable. A track implements only what makes its frozen contract suite pass —
  it never reshapes a frozen contract (amend the spec + re-approve instead, RULE-004).
- **Eval-first** (ADR-001: "the eval harness is the primary consumer"). Because C1 gives us
  `build_matcher` + models + null objects, tests and the eval harness target the **real
  decision core before any adapter is real**. Each integration slice (I1–I5) **writes its
  deterministic golden-table scenarios as the acceptance spec *before* wiring the logic.**
- **TDD** (conventions: "tests before or alongside to drive design", testing RULE-202). Each
  task is **red → green → refactor**: write the AAA, one-assertion test (RULE-001/004) + the
  **mandatory negative scenario** → simplest code to green → refactor under green → gates →
  review. The pure domain core makes test-first natural (no I/O to stub; testing RULE-102).
- **Two eval tiers stay honest:** deterministic hard-constraint evals **must be 100%** (the
  conventions exception); soft/LLM relevance evals treat **100% as a coverage warning**.

## Definition of Done — every PR

Extends the build-plan DoD; each task file references this list.

- [ ] **Test-first:** failing AAA test(s) before/with code; one assertion each (RULE-001/004);
      descriptive scenario names (RULE-003); no flaky tests (RULE-005).
- [ ] **Negative scenario present** (mandatory): no-viable-match, location-blocked,
      malformed-row, unverified-skill, or PII-leak attempt — whichever applies (RULE-104).
- [ ] **Right pyramid layer:** domain → `tests/unit/` (no mocks); port → `tests/contract/`
      suite (every adapter, real or null, passes it — `spec-driven-development.md` RULE-002);
      adapter → `tests/integration/` against a small real/fixture sample; scenario → `evals/`
      golden table (RULE-101/102).
- [ ] **Eval acceptance:** integration slices add/extend the deterministic golden table
      *first*; hard-constraint evals 100% green; PRs touching prompts/weights/scoring run
      `make eval` (heavy lane) and attach results.
- [ ] **Architecture:** dependency rule holds; infra errors mapped to domain errors at the
      boundary; adapters validate input and fail loudly (no silent drops).
- [ ] **Quality gates green:** `make format`, `make test`, `make lint` (incl. mypy strict).
- [ ] **Logging/security:** structured flat key-value logs only, no `print` outside the CLI;
      **no PII/secrets logged** (security RULE-006); secrets from env only (RULE-001); LLM
      calls + PII-scrubbing actions logged for audit.
- [ ] **Explainability:** every new factor that moved the rank appended as an
      `ExplanationFactor` and surfaced (Principle 1).
- [ ] **Reviewed & approved** (`task-execution.md`), then committed via PR — Conventional
      Commits, branch `type/short-desc`, reviewable in <30 min (`git-rules.md`).

## What cannot be parallelized (and why)

- **S0 then C1 are irreducibly serial.** Parallelism in ports-and-adapters is *purchased* by
  a stable port/model surface — you cannot fan out before the fan-out boundary exists. Both
  are small PRs; that is the entire cost.
- **I1 → I2** are serial against each other (I2 builds on I1's wired matcher + CLI). Beyond
  that, integration slices fan out again (I3‖I4; I5/I6/I7 after I4).
- Editing the *same* `scoring.py` formula or `Explanation` record from multiple tracks is the
  one thing no sequencing can fix — which is exactly why rules 1 and 2 above exist.
