# Staffeer — Build Plan

The complete, task-level plan to build Staffeer. Decomposed by **vertical slicing**
(`docs/commands/breakdown.md`): each slice delivers user-visible value end to end and is
shippable on its own. Follow the execution loop in `docs/rules/task-execution.md` —
**approve the spec/contract first** (`docs/rules/spec-driven-development.md`) → contract/unit
test → simplest solution → `make format/test/lint` → **review & approval** → mark `[x]` →
commit per `docs/rules/git-rules.md`.

State markers (`docs/rules/long-running-tasks.md`): `[ ]` not started · `[~]` in progress · `[x]` done.

> **Working as a team?** Read [`parallelization-guide.md`](parallelization-guide.md) first. The
> 9 slices below were chained serially because they edit the same files — not because of real
> data dependencies. Once the **ports + models are frozen** (S0 → C1), the work fans out into
> parallel tracks (A–F) plus thin integration-wiring PRs (I1–I7). The slice files keep their
> domain detail; the guide carries the sequencing, the per-PR Definition of Done, and the CI lanes.

## Slices & dependency order

```
S0 CI baseline (00a) ──► C1 Contracts wave 1 (00b) ──► fan-out: Tracks A,B,C,F
                                                  └──► C2 Contracts wave 2 ──► Tracks D,E

Tracks (parallel): A Domain core · B Data adapters · C PII · D Semantic · E LLM · F Evals

Integration wiring (thin PRs, each keeps main green):
  I1 Beach e2e ─► I2 Skill scoring ─► I3 Semantic blend ┐
                                   └─► I4 LLM soft score ┴─► I5 Supply expansion
                                                          ├─► I6 Relevance evals
                                                          └─► I7 Optional
```

**Irreducible critical path:** `S0 → C1` (two small PRs); after C1 everything fans out. The
shortest path to a shippable beach matcher is `S0 → C1 → (A-matching ‖ B-xlsx) → I1` — four hops.
The slice files 01–09 below map onto tracks + integration slices via the "Track / slice" column;
see [`parallelization-guide.md`](parallelization-guide.md) for ownership and ordering.

## Slice summaries (epics)

The **Track / slice** column maps each unit onto the parallel structure (S0/C1/C2 = serial
prerequisites; A–F = parallel tracks; I1–I7 = integration-wiring PRs). The original slice files
01–09 keep their full domain detail — only their headers and `Depends on:` lines were updated.

| # | Slice | Value delivered | Depends on | Track / slice | Detail |
|---|-------|-----------------|------------|---------------|--------|
| S0 | CI baseline | Green, runnable scaffold + CI fast lane on day one | — | serial #1 | `00a-ci-baseline.md` |
| C | Contracts | Frozen ports + models + null objects + composition root (the fan-out boundary) | S0 | serial #2 (C1, C2) | `00b-contracts.md` |
| 01 | Foundation | Project skeleton + xlsx load (now **split**: infra → S0, models/ports/xlsx → C1 + Tracks A/B) | — | S0 + C1 + A/B | `01-foundation.md` |
| 02 | Beach matching | CLI returns beach consultants who clear location + start date, with reasons | C1 | Track A (matching) + I1 | `02-beach-matching.md` |
| 03 | Skill matching | Shortlist scored/ordered by required-skill fit; gaps + adjacency explained | C1 | Track A (scoring) + I2 | `03-skill-matching.md` |
| 04 | Ingestion + PII | Profile PDFs + feedback parsed; PII scrubbed before any LLM use | C1 | Tracks B + C | `04-ingestion-pii.md` |
| 05 | Semantic retrieval | Semantic skill/profile matching complements lexical matching | C2, Track C | Track D + I3 | `05-semantic-retrieval.md` |
| 06 | LLM reasoning | Soft scoring + ranked, explained shortlist via LLM; free-text role | C2, Track C | Track E + I4 | `06-llm-reasoning-ranking.md` |
| 07 | Relevance evals | Promptfoo + DeepEval suites with negative scenarios; LLM-as-judge | I4, Track F | I6 | `07-relevance-evals.md` |
| 08 | Supply expansion | Roll-offs (date buffer, confidence) and new joiners (unverified skills) | I1 + (I2 or I4) | I5 | `08-supply-expansion.md` |
| 09 | Enhancements | Multi-role/team formation; optional web interface | I4 | I7 | `09-optional-enhancements.md` |

## Definition of done (every slice)

- [ ] Acceptance criteria in the slice file met.
- [ ] Unit tests for new domain logic; integration tests for new adapters; **negative scenarios** included.
- [ ] `make format`, `make test`, `make lint` all green.
- [ ] New ports/adapters respect the dependency rule (`docs/rules/hexagonal-architecture.md`).
- [ ] Explanations updated so every new factor is surfaced to the user (Principle 1).
- [ ] Reviewed and approved; committed via PR with Conventional Commits.

## How to work this plan

1. **Land the serial prerequisites first:** S0 ([`00a`](00a-ci-baseline.md)) then C1
   ([`00b`](00b-contracts.md)). Nothing else can be tested until these are green.
2. **After C1, pick up an unblocked track** (A/B/C/F; D/E after C2) per the ownership table in
   [`parallelization-guide.md`](parallelization-guide.md). Track work merges behind null-object
   defaults, so it never breaks `main`.
3. **Wire value via integration slices** (I1–I7): each is a thin PR that swaps a null object for
   a real adapter or flips a config flag. I1 is the first shippable beach matcher.
4. For each `[ ]` task: mark `[~]`, follow the per-PR **Definition of Done** in the guide
   (test-first + mandatory negative scenario → `make format/test/lint` → review & approval →
   mark `[x]` → commit per `git-rules.md`).
5. Use `/breakdown` to split any task that grows beyond ~4 hours, and `/clarify` for any
   ambiguous requirement before starting it.
