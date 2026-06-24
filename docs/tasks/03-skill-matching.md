# Slice 03 — Deterministic skill matching & gap explanations

**Goal:** order the eligible shortlist by required-skill fit and explain skill gaps and
adjacent-skill substitutions — all deterministic, before any LLM is involved.

**Type:** Feature · **Priority:** P0 · **Depends on:** C1 ([`00b-contracts.md`](00b-contracts.md))

> **Parallelization.** Scoring/ranking/explain are pure functions over `(role, consultant)` —
> **Track A**, mergeable after C1 independently of beach matching (02). Each lands as a named
> `ScoreContribution`; nobody edits a shared formula. CLI wiring is integration slice **I2**
> (depends on I1 + this track work). See [`parallelization-guide.md`](parallelization-guide.md).

## Acceptance criteria

- [x] Eligible consultants are scored 0..1 on required-skill coverage and ranked.
- [x] Output lists matched skills, missing skills, and adjacency substitutions (e.g. Java→Kotlin).
- [x] A configurable adjacency map drives substitutions; substitutions are scored lower than exact.
- [x] Roles where no one fully matches still return a ranked list with explicit gap explanations.

## Tasks

- [x] **Skill normalization** (`domain/skills.py`) — `canonical_skill` (case/space, strip
      `(expert)` qualifiers) + alias map (e.g. `k8s`→`kubernetes`); `canonical_skills` de-dups.
- [x] **Adjacency map** — data-driven `DEFAULT_ADJACENCY = {skill: (alternatives,)}`; seeded from
      the brief (Kotlin↔Java, etc.) with extension documented in the module docstring.
- [x] **Scorer** (`domain/scoring.py::skill_coverage`) — coverage = exact matches + weighted
      adjacency; pure function over `(role, consultant)` returning a `SkillScore` with detail.
- [x] **Ranker** (`domain/ranking.py`) — `skill_contribution` + `assemble_match` (score = sum of
      weighted contributions) + `rank` (best-first, ties broken by consultant name then id).
      Weight is passed in (no hard-coding); the `Matcher` supplies it from config at I2.
- [x] **Explainer** (`domain/explain.py`) — `skill_factor` (matched/adjacent/missing tally + detail)
      and `constraint_factors` (one factor per hard-constraint check); the open list later slices enrich.
- [x] **CLI** — extend `match` to show score + matched/missing/adjacent skills per consultant.
- [x] **Tests** — `tests/unit/test_skills.py`, `test_scoring.py`, `test_ranking.py`, `test_explain.py`:
      exact/partial coverage, adjacency-scored-lower, missing-skill gap text, ranking order + tie-break,
      and surfaced explanation factors. CLI/eval scenarios land at integration slice I2.
- [x] **Scenario evals** — extend golden table with skill-ranking expectations.

## Notes

- No semantic similarity yet — purely lexical + adjacency map. Slice 05 adds semantic matching.
- Keep weights in one config object so the business can re-tune (Principle 4).
