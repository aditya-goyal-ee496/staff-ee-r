# Slice 03 — Deterministic skill matching & gap explanations

**Goal:** order the eligible shortlist by required-skill fit and explain skill gaps and
adjacent-skill substitutions — all deterministic, before any LLM is involved.

**Type:** Feature · **Priority:** P0 · **Depends on:** C1 ([`00b-contracts.md`](00b-contracts.md))

> **Parallelization.** Scoring/ranking/explain are pure functions over `(role, consultant)` —
> **Track A**, mergeable after C1 independently of beach matching (02). Each lands as a named
> `ScoreContribution`; nobody edits a shared formula. CLI wiring is integration slice **I2**
> (depends on I1 + this track work). See [`parallelization-guide.md`](parallelization-guide.md).

## Acceptance criteria

- [ ] Eligible consultants are scored 0..1 on required-skill coverage and ranked.
- [ ] Output lists matched skills, missing skills, and adjacency substitutions (e.g. Java→Kotlin).
- [ ] A configurable adjacency map drives substitutions; substitutions are scored lower than exact.
- [ ] Roles where no one fully matches still return a ranked list with explicit gap explanations.

## Tasks

- [x] **Skill normalization** (`domain/skills.py`) — `canonical_skill` (case/space, strip
      `(expert)` qualifiers) + alias map (e.g. `k8s`→`kubernetes`); `canonical_skills` de-dups.
- [x] **Adjacency map** — data-driven `DEFAULT_ADJACENCY = {skill: (alternatives,)}`; seeded from
      the brief (Kotlin↔Java, etc.) with extension documented in the module docstring.
- [x] **Scorer** (`domain/scoring.py::skill_coverage`) — coverage = exact matches + weighted
      adjacency; pure function over `(role, consultant)` returning a `SkillScore` with detail.
- [ ] **Ranker** (`domain/ranking.py`) — order eligible results by score; deterministic tie-break
      (priority weighting → name). Configurable weights object (no hard-coding).
- [ ] **Explainer** (`domain/explain.py`) — assemble `Explanation` listing matched/missing/adjacent
      skills and the gap summary; this is the contract later slices enrich.
- [ ] **CLI** — extend `match` to show score + matched/missing/adjacent skills per consultant.
- [~] **Tests** — coverage scoring done (`tests/unit/test_skills.py`, `test_scoring.py`): exact,
      partial, adjacency-scored-lower, missing-skill gap text. Ranking tests land with the ranker.
- [ ] **Scenario evals** — extend golden table with skill-ranking expectations.

## Notes

- No semantic similarity yet — purely lexical + adjacency map. Slice 05 adds semantic matching.
- Keep weights in one config object so the business can re-tune (Principle 4).
