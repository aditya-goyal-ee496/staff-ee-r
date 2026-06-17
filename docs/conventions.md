# Conventions

Development standards for Staffeer. These are binding defaults; deviate only with a recorded
reason (an ADR, or a comment linking to one). Where a topic has a dedicated rule file in
`docs/rules/`, that file is authoritative and this page only summarizes + points to it.

## Toolchain

- **Language:** Python 3.12 (pinned via `mise` in `.mise.toml`).
- **Package manager / venv:** `uv` (`uv sync`, `uv add`, `uv run`). Commit `uv.lock`.
- **Formatter & linter:** `ruff` (format + lint) and `mypy` for type checking. Config in
  `pyproject.toml`. CI fails on `ruff check`, `ruff format --check`, and `mypy`.
- **Type hints are required** on all public functions, ports, and domain models.
- **Config from the environment** (`.env`, 12-factor — `docs/principles/12-factor-app.md`); no
  secrets in code (`docs/rules/security.md`).

## Directory structure

```
src/staffeer/
  domain/        # pure, deterministic core: models, scoring, ranking, explanation. No I/O.
    models.py    #   Pydantic: Consultant, Role, SupplyState, Match, Explanation
    matching.py  #   hard-constraint filtering
    scoring.py   #   skill / feedback / availability scoring + configurable weights
    ranking.py   #   ordering + tie-breaks
    explain.py   #   assemble human-readable, source-referenced rationale
  ports/         # Protocols / ABCs only — no concrete logic
                 #   ProfileParser, FeedbackStore, SupplyDemandSource,
                 #   SemanticIndex, LLMReasoner, PIIScrubber
  adapters/      # one module per external system, each implementing a port
    docling_profiles.py, xlsx_supply_demand.py, markdown_feedback.py,
    milvus_index.py, dspy_openrouter.py, presidio_pii.py
  config.py      # settings loaded from env (.env); no secrets in code
  cli/           # Typer entry point (driving adapter)
tests/
  unit/          # mirrors src/staffeer/; domain core has no mocks needed
  integration/   # adapters against real fixtures (sampled raw data)
evals/           # scenario evals now; Promptfoo + DeepEval suites + datasets later
docs/            # control plane: rules/, principles/, architecture/, adr/, tasks/, commands/
planning/        # raw-data only (git-ignored)
```

**Dependency rule** (`docs/rules/hexagonal-architecture.md`): `domain/` imports nothing from
`adapters/`, `cli/`, or third-party I/O libraries. Dependencies point inward. Adapters depend
on ports, never the reverse. Domain errors are defined in the core; infrastructure errors are
mapped to domain errors at the adapter boundary. No ORM/serialization annotations on domain
models.

**Domain modelling** (`docs/rules/domain-driven-design.md`): `Consultant`/`Role` are entities
(identity); `ConstraintCheck`/`Explanation` are immutable value objects; use the ubiquitous
language from the brief (beach, roll-off, new joiner, co-location, Chennai-open).

## Naming

- Files & modules: `snake_case.py`. Test files: `test_<module>.py`.
- Functions & variables: `snake_case`. Classes & Pydantic models: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`. Ports: noun + role (`ProfileParser`, `LLMReasoner`).
- Adapters: named for the technology they wrap (`milvus_index.py`, `dspy_openrouter.py`) so
  swapping an implementation is obvious.
- See `docs/rules/clean-code.md`: intention-revealing names, functions <20 lines doing one
  thing, <=3 parameters, avoid >3 nesting levels, no dead/commented-out code.

## Testing (`docs/rules/testing-principles.md`)

- One clear assertion per test; Arrange-Act-Assert; descriptive names stating scenario +
  outcome (e.g. `no_viable_match_returns_zero_eligible`). Tests are independent and order-free.
- **Test pyramid:** many unit tests > fewer integration tests > minimal e2e. Test doubles only
  for external dependencies — never mock domain logic.
- **Domain core:** unit-tested directly, deterministic. Cover hard-constraint logic (location,
  dates) exhaustively — these must be repeatable.
- **Adapters:** integration-tested against small real fixtures sampled from `raw-data`.
- **LLM behaviour:** evaluated via `evals/`, not brittle string equality. DeepEval metrics
  (relevance, faithfulness) + Promptfoo scenarios once the LLM path lands.
- **Negative scenarios are required**: roles with no viable match, location-blocked candidates,
  unverified-skill new joiners, adjacent-skill substitutions. A *relevance* suite that scores
  100% is treated as under-covered. Deterministic hard-constraint evals are the exception —
  they must be perfect. Fix or delete flaky tests immediately.
- Run `make test` on every change; `make eval` before merging anything touching prompts,
  scoring weights, or the LLM path.

## Error handling & logging (`docs/rules/code-quality.md`)

- **No silent failures.** Catch *specific* exceptions, never the base class except in a top-level
  handler. Never log-and-rethrow. Add context via typed `StaffeerError` subclasses at boundaries.
- When the system cannot satisfy a requirement, it **explains the gap** (missing skill, location
  conflict, no availability) rather than fabricating or silently dropping a match.
- Validate all external input (xlsx, PDF, env) at the adapter boundary with Pydantic; fail loudly.
- **Structured logging only:** flat key-value pairs (role id, consultant id, stage), consistent
  keys/units, no prose storytelling. One config in `config.py`; no `print` outside the CLI layer.
- Log LLM calls (model, tokens, latency) and PII-scrubbing actions for auditability.

## Security & governance (`docs/rules/security.md`)

- Secrets (OpenRouter key) come from `.env` only; `.env` is git-ignored. Never commit keys.
- Validate/sanitize input at every boundary; reject malformed data. Never log PII, tokens, or keys.
- Run `PIIScrubber` (Presidio + spaCy) on profile/feedback text before it reaches the LLM.
- Raw data in `planning/raw-data/` is git-ignored and must stay that way.

## Architecture documentation (`docs/rules/likec4.md`)

- **LikeC4 is canonical:** model + views live in `docs/architecture/*.c4` with a
  `likec4.config.json` at repo root. Every element carries business-meaningful descriptions and
  source metadata; tags are `UPPER_CASE`; technology strings are specific (`python`, `Typer`,
  `Milvus Lite`); single quotes for values; naming is kebab-case throughout.
- `docs/architecture/L1-system-context.md` and `L2-containers.md` hold rendered **Mermaid**
  mirrors for quick reading; keep them in sync with the `.c4` model when the architecture changes.

## Git workflow (`docs/rules/git-rules.md`)

- **Conventional Commits:** `type(scope): description` — `feat|fix|chore|docs|refactor|test|ci`;
  imperative present tense; subject <72 chars; body explains *why*; reference work items
  (`Refs: docs/tasks/02-...`).
- **Branches:** `type/short-description` (e.g. `feat/beach-matching`) off `main`. Never commit
  directly to `main`.
- **PRs:** small, reviewable in <30 min; squash WIP/fixup commits; describe what/why/how-to-test;
  delete the branch after merge. All CI checks (lint + test) must pass. PRs touching
  scoring/prompts must show eval results. Delete branches after merging.

## Task workflow (`docs/rules/task-execution.md`, `docs/rules/long-running-tasks.md`)

- Multi-stage work is tracked as markdown checklists in `docs/tasks/`: `[ ]` not started,
  `[~]` in progress (update the item in place; add subtasks/detail under it), `[x]` done.
  Each checklist must carry enough detail to resume with empty context.
- Execution loop: implement the simplest solution -> `make format`/`test`/`lint` ->
  **request review and wait for approval** -> mark `[x]` -> commit per git-rules.

## SOLID & clean code

`docs/rules/solid-principles.md` (SRP; depend on abstractions; <=5 deps per class; shallow
hierarchies; dependency injection) and `docs/rules/clean-code.md` apply to all production code.

## Applicable rule files (index)

| Concern | File |
|---|---|
| Architecture / ports & adapters | `docs/rules/hexagonal-architecture.md` |
| Domain modelling | `docs/rules/domain-driven-design.md` |
| OO design | `docs/rules/solid-principles.md` |
| Readability | `docs/rules/clean-code.md` |
| Errors & logging | `docs/rules/code-quality.md` |
| Tests | `docs/rules/testing-principles.md` |
| Security | `docs/rules/security.md` |
| HTTP/API (future web adapter) | `docs/rules/api-design.md` |
| Diagrams | `docs/rules/likec4.md` |
| Git | `docs/rules/git-rules.md` |
| Task execution | `docs/rules/task-execution.md`, `docs/rules/long-running-tasks.md` |
