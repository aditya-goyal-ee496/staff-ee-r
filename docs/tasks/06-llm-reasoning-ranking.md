# Slice 06 — LLM reasoning, soft scoring & ranking

**Goal:** add the soft-judgment layer — fit, adjacency willingness, feedback weighting — via an
LLM behind a port, producing the final ranked, explained shortlist. Free-text role queries
become possible here.

**Type:** Feature · **Priority:** P0 · **Depends on:** 05

## Acceptance criteria

- [ ] `LLMReasoner` port implemented with DSPy over OpenRouter (local model also supported).
- [ ] Soft factors (team fit, adjacent-skill willingness, feedback sentiment, beach trajectory)
      produce a soft score combined with deterministic scores via configurable weights.
- [ ] Final shortlist is ranked and each entry has a rationale citing its sources (referenceability).
- [ ] CLI accepts a **free-text role** ("backend engineer with database experience") in addition to ids.
- [ ] All text sent to the LLM is PII-scrubbed (slice 04); LLM calls are logged (model/tokens/latency).
- [ ] The reasoner explains gaps and abstains rather than fabricating when evidence is thin.

## Tasks

- [ ] **Port** — `LLMReasoner.assess(role, candidate, evidence) -> SoftAssessment` (score + rationale
      + cited sources) (`ports/`).
- [ ] **DSPy adapter** (`adapters/dspy_openrouter.py`) — configure DSPy LM via OpenRouter key from
      env; signatures for fit/feedback assessment; deterministic settings where repeatability matters
      (`docs/rules/` — decide-where-variance-is-allowed).
- [ ] **Free-text role parsing** — DSPy signature to extract required skills/seniority/constraints
      from a free-text query into a `Role`-like structure; validate the result.
- [ ] **Soft scoring + blend** — combine hard (02) + lexical (03) + semantic (05) + soft (06) scores
      with a single weights config; document defaults and rationale.
- [ ] **Explainer** — extend `Explanation` with the LLM rationale and source citations; ensure every
      factor that moved the rank is shown.
- [ ] **Tests** — unit tests with a stubbed `LLMReasoner` (no network) for scoring/ranking/abstention;
      an integration test gated on `OPENROUTER_API_KEY` presence.
- [ ] **ADR** — record the LLM provider/model + the variance/determinism policy.

## Notes

- Do not mock domain logic in tests; only stub the `LLMReasoner` port (`docs/rules/testing-principles.md`).
- Keep prompts/signatures versioned; changes here require eval results in the PR.
