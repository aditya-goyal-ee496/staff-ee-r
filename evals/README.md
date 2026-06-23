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

## 2. Soft / relevance evals (later — Promptfoo + DeepEval)

When the semantic and LLM tracks land, relevance suites (LLM-as-judge) join the heavy CI lane.
For those, **100% is treated as a coverage warning, not a pass** (ADR-001): full marks signal the
suite is too easy, not that the system is perfect. They are not wired yet.
