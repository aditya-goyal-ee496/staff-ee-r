# Slice 01 — Foundation

**Goal:** a runnable, tested Python project skeleton where the demand-supply workbook loads
into typed domain models through a port + adapter. No matching logic yet.

**Type:** Task (technical) · **Priority:** P0 · **Depends on:** none

> **Parallelization (superseded — kept for detail).** This slice has been **split** to give the
> team a green baseline before any domain content, and to make the models/ports a frozen fan-out
> boundary. Execute it as three units, not one:
> - **Project config / tooling / package skeleton / `.env.example` / CI** → **S0**
>   ([`00a-ci-baseline.md`](00a-ci-baseline.md)).
> - **Domain models + `SupplyDemandSource` port** → **C1** ([`00b-contracts.md`](00b-contracts.md)),
>   where they are frozen with all optional fields pre-baked.
> - **xlsx adapter + its tests** → **Track B**, wired into the matcher by **I1** (see
>   [`02-beach-matching.md`](02-beach-matching.md) and [`parallelization-guide.md`](parallelization-guide.md)).
> The tasks below remain the authoritative spec for *what* to build in each unit.

## Acceptance criteria

- [ ] `make install` provisions the venv; `make test`, `make lint`, `make format` run.
- [x] `XlsxSupplyDemandSource` loads Open Roles + all three supply tabs into `Role`/`Consultant`.
- [ ] Domain models are pure Pydantic with no I/O imports (dependency rule holds).
- [x] Integration test loads the real workbook (skipped when data absent).

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
- [x] **xlsx adapter** (`adapters/xlsx_supply_demand.py`) — parses the `as of` title date, header
      row, skips empty padding; normalizes all four tabs (incl. per-consultant Chennai-open and
      role co-location → `chennai_open`). Raises `SupplyDemandError` on malformed
      date/priority/confidence (fail loudly). Beach `available_from` = as-of; new joiners
      `skills_verified=False`; rolling-off confidence text → weight.
- [ ] **`.env.example`** — `OPENROUTER_API_KEY=`, commented `STAFFEER_DATA`.
- [x] **Tests** — adapter parsing against a fixture workbook (`tests/conftest.py::workbook_factory`)
      + the shared `SupplyDemandSource` contract suite now parametrised over the xlsx adapter
      (`tests/contract/`); integration loads the real workbook (`skipif` absent). Malformed
      date/priority negative cases covered.
- [ ] **CI** — GitHub Actions running `make lint` + `make test` on PRs (`docs/rules/git-rules.md`).

## Notes

- Heavy LLM/NLP deps stay in optional groups so `make install` is fast until their slices land.
- A fixture workbook keeps adapter unit tests runnable without the git-ignored real data.
