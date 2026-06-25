# Evals

Staffeer is built eval-first: the eval harness is a primary consumer of the decision core, not an
afterthought (ADR-001). There are **two tiers**, kept honest by different pass criteria.

## 1. Deterministic hard-constraint scenarios (this directory)

`test_constraint_scenarios.py` is a **golden table**: each scenario fixes a role and a supply
pool and asserts the exact ranked shortlist and the exact set of explained exclusions. These
cover the repeatable, LLM-free decisions (location, availability, deterministic skill coverage).

- **Must be 100% green.** A failure here is a regression in the decision core.
- Includes the mandatory **negative scenario** (no viable match) so exclusions stay explainable.
- Run with `make eval` (currently `uv run pytest evals`).

## 2. Soft / relevance evals (Promptfoo scenario coverage + DeepEval LLM-judge)

Two sub-layers make up the soft lane:

### 2a. Promptfoo scenario coverage (`evals/promptfoo.yaml`)

An exec provider drives `evals/promptfoo_provider.py`, which runs the core Matcher with
null adapters (no network, no LLM cost) against scenarios from `evals/datasets/role_scenarios.py`.
Positive scenarios assert expected consultant names appear in the shortlist; negative scenarios
vary by type — hard-exclusion scenarios (no-viable-match, location-blocked) assert an empty
shortlist, while provenance-penalty scenarios (unverified-new-joiner, adjacent-skill-only) assert
the consultant IS present but flagged, not silently dropped.

> **Known gap:** the assertion for `negative-unverified-new-joiner` previously used
> `result.shortlist.length >= 0`, which is vacuous (always true). It has been corrected
> to `result.shortlist.includes("Nisha")` — the meaningful claim is that Nisha appears
> despite low trust, not that the array is non-empty. The same fix applies to
> `negative-adjacent-skill-only`. Any future negative scenario that intends to assert
> presence (not emptiness) must name the specific consultant, not check array length.

Run via: `npx promptfoo eval --config evals/promptfoo.yaml`

### 2b. DeepEval LLM-judge (`evals/deepeval/`)

`test_relevance_scenarios.py` scores shortlist relevance (threshold 0.7).
`test_faithfulness_scenarios.py` scores rationale faithfulness (threshold 0.6).
Both use versioned judge prompts from `evals/deepeval/judge_prompts.py`.

**100% pass rate on relevance or faithfulness is a COVERAGE WARNING, not success (ADR-001).**
Full marks signal the scenarios are too easy.  When you see 100%, add harder scenarios.

### Mandatory negative scenario types

The dataset must contain at least four negative scenarios:

1. **no-viable-match** — no consultant meets the role's location; shortlist must be empty.
2. **location-blocked** — Chennai co-located role, all consultants lack `chennai_open`.
3. **unverified-new-joiner** — `NEW_JOINER` with `skills_verified=False`; provenance penalty.
   Nisha IS present on the shortlist with an unverified-skills flag — she is not excluded.
4. **adjacent-skill-only** — role needs kotlin, consultant has only java (adjacent, not exact).
   Ivan IS present on the shortlist with a gap note — he is not excluded.

### Heavy-lane trigger

DeepEval suites (`evals/deepeval/`) run on the **heavy lane** only:
- On a weekly schedule (Monday 04:00 UTC via `.github/workflows/integration.yml`), or
- When a PR carries the **`run-heavy`** label.

They require `uv sync --extra eval` and `OPENROUTER_API_KEY` in the environment.
The deterministic scenarios (`evals/` excluding `evals/deepeval/`) always run with `make eval`.

### Dataset

Scenario definitions and synthetic consultant fixtures live in `evals/datasets/role_scenarios.py`.
All synthetic consultants carry `source='synthetic'`.

### Reporting (pending)

CLAUDE.md's Git workflow rule requires PRs touching scoring/prompts to include eval results.
The mechanism to surface the eval summary in those PRs (a CI step, PR template section, or
`make eval` output-posting workflow) is tracked as an open item in
`docs/tasks/07-relevance-evals.md` (`Reporting — eval summary surfaced in PRs that touch
prompts/weights`) and has not yet been implemented. Until that item is closed, authors must
manually paste `make eval` output into PR descriptions when changing prompts or weights.
