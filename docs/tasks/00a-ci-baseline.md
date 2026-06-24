# Slice S0 — CI baseline (green scaffold)

**Goal:** a runnable repo that is **green in CI on day one** — toolchain, quality gates, and
an empty package skeleton — so every later PR has a passing baseline to build on. This is the
*infrastructure* half of the old slice 01 (its *content* — models/ports/xlsx — moves to
[`00b-contracts.md`](00b-contracts.md) and Tracks A/B).

**Type:** Task (technical) · **Priority:** P0 · **Depends on:** none ·
**Parallelization:** the single irreducible first step — nothing else can be built or tested
until this lands. Keep it tiny (one reviewer, <30 min). See
[`parallelization-guide.md`](parallelization-guide.md).

## Acceptance criteria

- [x] `make install` provisions the venv; `make test`, `make lint`, `make format` all run and pass.
- [x] CI **fast lane** runs `make lint` + `make test` on every PR and on push to `main`, and is green.
- [x] The package imports and `config.py` reads env without secrets in code.
- [x] Heavy LLM/NLP deps live in optional groups so `make install` stays fast.

## Tasks

- [x] **Project config** — `pyproject.toml` (uv, hatchling), `.mise.toml` (python 3.12, uv),
      `.python-version`. Core deps: `pydantic`, `openpyxl`, `typer`. Optional groups:
      `llm` (dspy), `nlp` (presidio, spacy, pymilvus), `parse` (docling), `eval` (deepeval).
      Dev group: `pytest`, `ruff`, `mypy`.
- [x] **Tooling config** — ruff (line-length 100, `E,F,I,UP,B,SIM`), mypy strict, pytest
      (`pythonpath=src`, `testpaths=tests`). Wire `Makefile` targets to real commands.
- [x] **Package skeleton** — `src/staffeer/{__init__,config}.py` and empty
      `domain/ ports/ adapters/ cli/` packages. `config.py` reads `STAFFEER_DATA` +
      `OPENROUTER_API_KEY` from env (12-factor; no secrets in code).
- [x] **`.env.example`** — `OPENROUTER_API_KEY=`, commented `STAFFEER_DATA`.
- [x] **Trivial test** — one passing unit test (e.g. config loads defaults) so `make test` is green.
- [x] **CI fast lane** (`.github/workflows/ci.yml`) — install core deps only, run `make lint`
      + `make test`; required for merge (`CLAUDE.md` (Git workflow)). No secrets, no
      network, no heavy models. The **heavy lane** (`integration.yml`) is scaffolded in
      [`00b-contracts.md`](00b-contracts.md)/Track F as the real-data + relevance evals land.

## Notes

- This split exists so the team gets a green gate *before* any domain content is written —
  every subsequent PR (contracts, tracks, integration) merges against a passing baseline.
- Branch-protect `main`: require the fast lane to pass; heavy lane is informational here.
- Definition of Done: see [`parallelization-guide.md`](parallelization-guide.md).
