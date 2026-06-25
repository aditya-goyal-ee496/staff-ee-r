# Slice 07 — Relevance eval harness

**Goal:** evaluate the open-ended quality of recommendations with Promptfoo (scenario coverage)
and DeepEval (relevance/faithfulness), including negative scenarios and an LLM-as-judge.

**Type:** Task (quality) · **Priority:** P0 · **Depends on:** I4 + Track F (eval scaffolding)

> **Parallelization.** The deterministic eval *scaffolding* (golden-table harness, `evals/README`,
> heavy-lane `integration.yml`) is **Track F** and can start right after C1 — each integration
> slice grows its golden table as its acceptance spec. This slice = integration **I6**: the LLM
> relevance suites (Promptfoo + DeepEval, LLM-as-judge) that run only on the **heavy lane**
> (scheduled / `run-heavy` label). A relevance suite scoring 100% is a coverage *warning*, never a
> pass. See [`parallelization-guide.md`](parallelization-guide.md).

## Acceptance criteria

- [x] Promptfoo config drives a curated set of role scenarios (positive + negative) through the CLI/core.
- [x] DeepEval metrics score relevance and faithfulness of the shortlist + rationale.
- [x] Negative scenarios included (no viable match, location-blocked, unverified new joiner,
      adjacent-skill case); synthetic data added where the dataset lacks them.
- [x] A relevance suite scoring 100% triggers a coverage review (treated as a warning, not success).
- [x] `make eval` runs deterministic scenario evals AND the relevance suites.

## Tasks

- [x] **Datasets** (`evals/datasets/`) — golden role scenarios with expected qualitative outcomes;
      label positives/negatives; document provenance of any synthetic data.
- [x] **Promptfoo** (`evals/promptfoo.yaml`) — providers/prompts wired to the matcher; assertions
      for must-include / must-exclude candidates and explanation properties.
- [x] **DeepEval** (`evals/deepeval/`) — relevance + faithfulness metrics; LLM-as-judge config;
      thresholds chosen deliberately (not 100%).
- [x] **Make / CI** — `make eval` runs both layers; CI runs deterministic evals always and relevance
      evals on a schedule or label (LLM cost-aware).
- [x] **Reporting** — eval summary surfaced in PRs that touch prompts/weights (`CLAUDE.md → Git workflow`).

## Notes

- Relevance, not accuracy, is the primary signal for this open-ended system (README guiding principles).
- Keep LLM-judge prompts versioned alongside the suites.
