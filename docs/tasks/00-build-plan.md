# Staffeer — Build Plan

The complete, task-level plan to build Staffeer. Decomposed by **vertical slicing**
(`docs/commands/breakdown.md`): each slice delivers user-visible value end to end and is
shippable on its own. Follow the execution loop in `docs/rules/task-execution.md` — simplest
solution → `make format/test/lint` → **review & approval** → mark `[x]` → commit per
`docs/rules/git-rules.md`.

State markers (`docs/rules/long-running-tasks.md`): `[ ]` not started · `[~]` in progress · `[x]` done.

## Slices & dependency order

```
01 Foundation (scaffold, models, xlsx adapter)
        │
02 Beach-only hard-constraint matching (CLI end-to-end)   ← first shippable slice
        │
03 Deterministic skill matching & gap explanations
        │
04 Profiles + feedback ingestion + PII scrubbing ──┐
        │                                           │
05 Semantic retrieval (Milvus Lite) ───────────────┘
        │
06 LLM reasoning, soft scoring & ranking (DSPy/OpenRouter)
        │
07 Relevance eval harness (Promptfoo + DeepEval)
        │
08 Supply expansion (roll-offs, new joiners)
        │
09 Optional: multi-role / team formation, web UI
```

Critical path: 01 → 02 → 03 → 04 → 05 → 06 → 07. Slice 08 depends on 02 + 06. Slice 09 is optional.
Slices 04 and 05 can overlap once 03 is done.

## Slice summaries (epics)

| # | Slice | Value delivered | Depends on | Detail |
|---|-------|-----------------|------------|--------|
| 01 | Foundation | A runnable, tested project skeleton; data loads into typed models | — | `01-foundation.md` |
| 02 | Beach matching | CLI returns beach consultants who clear location + start date for a role, with reasons | 01 | `02-beach-matching.md` |
| 03 | Skill matching | Shortlist scored/ordered by required-skill fit; gaps + adjacency explained (deterministic) | 02 | `03-skill-matching.md` |
| 04 | Ingestion + PII | Profile PDFs + feedback parsed; PII scrubbed before any LLM use | 02 | `04-ingestion-pii.md` |
| 05 | Semantic retrieval | Semantic skill/profile matching complements lexical matching | 03, 04 | `05-semantic-retrieval.md` |
| 06 | LLM reasoning | Soft scoring (fit, adjacency, feedback weighting) + ranked, explained shortlist via LLM | 05 | `06-llm-reasoning-ranking.md` |
| 07 | Relevance evals | Promptfoo + DeepEval suites with negative scenarios; LLM-as-judge relevance | 06 | `07-relevance-evals.md` |
| 08 | Supply expansion | Roll-offs (date buffer, confidence) and new joiners (unverified skills) | 02, 06 | `08-supply-expansion.md` |
| 09 | Enhancements | Multi-role/team formation; optional web interface | 06 | `09-optional-enhancements.md` |

## Definition of done (every slice)

- [ ] Acceptance criteria in the slice file met.
- [ ] Unit tests for new domain logic; integration tests for new adapters; **negative scenarios** included.
- [ ] `make format`, `make test`, `make lint` all green.
- [ ] New ports/adapters respect the dependency rule (`docs/rules/hexagonal-architecture.md`).
- [ ] Explanations updated so every new factor is surfaced to the user (Principle 1).
- [ ] Reviewed and approved; committed via PR with Conventional Commits.

## How to work this plan

1. Open the lowest-numbered slice with unstarted tasks.
2. Take the first `[ ]` task with no unmet dependency; mark it `[~]`.
3. Execute per `task-execution.md`; on approval mark `[x]` and commit.
4. When a slice's acceptance criteria are all met, move to the next slice.
5. Use `/breakdown` to split any task that grows beyond ~4 hours, and `/clarify` for any
   ambiguous requirement before starting it.
