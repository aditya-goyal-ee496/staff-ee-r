# Slice 01 — Foundation

**Goal:** a runnable, tested Python project skeleton where the demand-supply workbook loads
into typed domain models through a port + adapter. No matching logic yet.

**Type:** Task (technical) · **Priority:** P0 · **Depends on:** none

## Acceptance criteria

- [ ] `make install` provisions the venv; `make test`, `make lint`, `make format` run.
- [ ] `XlsxSupplyDemandSource` loads Open Roles + all three supply tabs into `Role`/`Consultant`.
- [ ] Domain models are pure Pydantic with no I/O imports (dependency rule holds).
- [ ] Integration test loads the real workbook (skipped when data absent).

## Tasks

- [ ] **Project config** — `pyproject.toml` (uv, hatchling), `.mise.toml` (python 3.12, uv),
      `.python-version`. Core deps: `pydantic`, `openpyxl`, `typer`. Optional groups:
      `llm` (dspy), `nlp` (presidio, spacy, pymilvus), `parse` (docling), `eval` (deepeval).
      Dev group: `pytest`, `ruff`, `mypy`.
- [ ] **Tooling config** — ruff (line-length 100, `E,F,I,UP,B,SIM`), mypy strict, pytest
      (`pythonpath=src`, `testpaths=tests`). Wire `Makefile` targets to real commands.
- [ ] **Package skeleton** — `src/staffeer/{__init__,config}.py` and empty
      `domain/ ports/ adapters/ cli/` packages. `config.py` reads `STAFFEER_DATA` +
      `OPENROUTER_API_KEY` from env (12-factor; no secrets in code).
- [ ] **Domain models** (`domain/models.py`) — `SupplyState`, `Priority` enums; `Consultant`,
      `Role` (frozen Pydantic). Skills as `list[str]`; dates as `date`. Ubiquitous language
      from the brief (`docs/rules/domain-driven-design.md`).
- [ ] **Port** (`ports/supply_demand.py`) — `SupplyDemandSource` Protocol: `open_roles()`,
      `role(id)`, `consultants(*states)`.
- [ ] **xlsx adapter** (`adapters/xlsx_supply_demand.py`) — parse title row for `as of` date,
      header row, skip empty padding. Normalize all four tabs. Raise `SupplyDemandError` on
      malformed dates/priority (fail loudly, no silent drops). Beach `available_from` = as-of date.
- [ ] **`.env.example`** — `OPENROUTER_API_KEY=`, commented `STAFFEER_DATA`.
- [ ] **Tests** — unit: model validation + adapter parsing against a tiny in-repo fixture xlsx;
      integration: load real workbook, `skipif` data absent. Cover a malformed-row negative case.
- [ ] **CI** — GitHub Actions running `make lint` + `make test` on PRs (`docs/rules/git-rules.md`).

## Notes

- Heavy LLM/NLP deps stay in optional groups so `make install` is fast until their slices land.
- A fixture workbook keeps adapter unit tests runnable without the git-ignored real data.
