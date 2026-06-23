# Slice 02 — Beach-only hard-constraint matching

**Goal:** the first shippable vertical slice — a CLI that, given a role id, returns the beach
consultants who clear the **hard constraints** (location, start date), each with a reason, and
explains exclusions.

**Type:** Feature · **Priority:** P0 · **Depends on:** C1 ([`00b-contracts.md`](00b-contracts.md))

> **Parallelization.** The constraint logic (`eligibility.py`, value objects) is **Track A** —
> mergeable anytime after C1 behind null-object wiring. The CLI + xlsx wiring that makes this the
> first shippable matcher is integration slice **I1** (depends on Track A matching + Track B xlsx).
> See [`parallelization-guide.md`](parallelization-guide.md) for the per-PR Definition of Done.

## Acceptance criteria

- [x] `make match ROLE="ROLE-02"` prints eligible beach consultants with their grade/location/skills.
- [x] Location logic: co-located Chennai role honours `Chennai-open`; co-located non-Chennai needs
      same city; remote-India roles accept any India location; city-specific non-remote needs same city.
- [x] Start-date logic: available by `role.start + buffer` (default 7 days); beach = available now.
- [x] Every excluded consultant carries a human-readable reason (no silent drops).
- [x] `--show-excluded` lists exclusions with reasons.

## Tasks

- [x] **Constraint value objects** (`domain/models.py`) — `ConstraintCheck(name, passed, reason)`
      and `EligibilityResult(consultant, checks)` with `eligible`/`failures` (immutable). (C1)
- [x] **Location constraint** (`domain/eligibility.py::location_constraint`) — parse role location
      into city + region/remote; implement the four cases above; Chennai uses the `chennai_open` signal.
- [x] **Availability constraint** (`availability_constraint`) — `available_from <= start + buffer`;
      buffer configurable; reason states the dates and computed latest-acceptable.
- [x] **Screen** (`screen_consultants`) — evaluate all beach consultants; return results for all
      (eligible first) so exclusions are explainable.
- [x] **CLI** (`cli/main.py`) — Typer app: `roles` (list) and `match ROLE_ID [--data] [--show-excluded]`,
      `staffeer` console script. Maps `SupplyDemandError` / role-not-found to a clear message + exit 1. (I1)
- [x] **Unit tests** (`tests/unit/test_eligibility.py`) — each location case (incl. Chennai-open
      positive/negative), availability pass/fail/within-buffer, ordering, and the **no-viable-match**
      negative scenario.
- [x] **Scenario evals** (`evals/test_constraint_scenarios.py`) — golden table incl. the
      no-viable-match negative; deterministic, 100% green. `evals/README.md` describes the two layers.
- [x] Point `make eval` at `uv run pytest evals` for now.

## Notes

- Free-text role parsing ("backend engineer …") arrives with the LLM slice (06); until then
  `match` takes a sheet role id. Document this in `--help`.
- Keep `eligibility.py` pure — no I/O, no logging side effects in the constraint functions.
