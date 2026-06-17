# Slice 03 — Deterministic skill matching & gap explanations

**Goal:** order the eligible shortlist by required-skill fit and explain skill gaps and
adjacent-skill substitutions — all deterministic, before any LLM is involved.

**Type:** Feature · **Priority:** P0 · **Depends on:** 02

## Acceptance criteria

- [ ] Eligible consultants are scored 0..1 on required-skill coverage and ranked.
- [ ] Output lists matched skills, missing skills, and adjacency substitutions (e.g. Java→Kotlin).
- [ ] A configurable adjacency map drives substitutions; substitutions are scored lower than exact.
- [ ] Roles where no one fully matches still return a ranked list with explicit gap explanations.

## Tasks

- [ ] **Skill normalization** (`domain/skills.py`) — case/space normalization, alias map
      (e.g. `k8s`→`kubernetes`), parse role required-skills (split `;`, strip `(expert)` qualifiers).
- [ ] **Adjacency map** — data-driven `{skill: [acceptable_alternatives]}`; seed from the brief
      (Kotlin↔Java, etc.). Document how to extend it.
- [ ] **Scorer** (`domain/scoring.py`) — coverage score = exact matches + weighted adjacency;
      pure function over `(role, consultant)` returning a `SkillScore` value object with detail.
- [ ] **Ranker** (`domain/ranking.py`) — order eligible results by score; deterministic tie-break
      (priority weighting → name). Configurable weights object (no hard-coding).
- [ ] **Explainer** (`domain/explain.py`) — assemble `Explanation` listing matched/missing/adjacent
      skills and the gap summary; this is the contract later slices enrich.
- [ ] **CLI** — extend `match` to show score + matched/missing/adjacent skills per consultant.
- [ ] **Tests** — exact-match ranking, adjacency substitution scored lower, missing-skill gap text,
      and a **partial-coverage** negative scenario (nobody fully matches).
- [ ] **Scenario evals** — extend golden table with skill-ranking expectations.

## Notes

- No semantic similarity yet — purely lexical + adjacency map. Slice 05 adds semantic matching.
- Keep weights in one config object so the business can re-tune (Principle 4).
