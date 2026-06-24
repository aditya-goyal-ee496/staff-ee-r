# Conventions

Development standards for Staffeer. These are binding defaults; deviate only with a recorded
reason (an ADR, or a comment linking to one). Where a topic has a dedicated file under
`.claude/principles/` (engineering principles) or `.claude/rules/` (how-to guidelines), that file
is authoritative and this page only summarizes + points to it. The process workflow (spec-driven
development, task execution, resumable checklists, git conventions) is owned by `CLAUDE.md` →
**Development workflow** and the `/specify` / `/build-feature` / `/orchestrate` workflows.

## Toolchain

- **Language:** Python 3.12 (pinned via `mise` in `.mise.toml`).
- **Package manager / venv:** `uv` (`uv sync`, `uv add`, `uv run`). Commit `uv.lock`.
- **Formatter & linter:** `ruff` (format + lint) and `mypy` for type checking. Config in
  `pyproject.toml`. CI fails on `ruff check`, `ruff format --check`, and `mypy`.
- **Type hints are required** on all public functions, ports, and domain models.
- **Config from the environment** (`.env`, 12-factor — `.claude/principles/12-factor-app.md`); no
  secrets in code (`.claude/principles/security.md`).

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
  contract/      # executable specs: one suite per port; EVERY adapter must pass its port's suite
  unit/          # mirrors src/staffeer/; domain core has no mocks needed
  integration/   # adapters against real fixtures (sampled raw data)
evals/           # scenario evals now; Promptfoo + DeepEval suites + datasets later
docs/            # domain context: architecture/, adr/, tasks/, conventions.md
.claude/         # control plane: principles/, rules/, commands/, orchestration/
planning/        # raw-data only (git-ignored)
```

**Spec-driven** (`.claude/commands/specify.md`): the **port is the spec**. All port
Protocols, domain value objects, and their `tests/contract/` suites are frozen in the **C1/C2
contract waves** (`docs/tasks/00b-contracts.md`) and **approved before** implementation begins.
Each port's contract suite is the executable spec the null object and every real adapter must
pass. Freezing these contracts up front is the fan-out boundary that lets Tracks A–F run **in
parallel** (`docs/tasks/parallelization-guide.md`).

**Dependency rule** (`.claude/principles/hexagonal-architecture.md`): `domain/` imports nothing from
`adapters/`, `cli/`, or third-party I/O libraries. Dependencies point inward. Adapters depend
on ports, never the reverse. Domain errors are defined in the core; infrastructure errors are
mapped to domain errors at the adapter boundary. No ORM/serialization annotations on domain
models.

**Domain modelling** (`.claude/principles/domain-driven-design.md`): `Consultant`/`Role` are entities
(identity); `ConstraintCheck`/`Explanation` are immutable value objects; use the ubiquitous
language from the brief (beach, roll-off, new joiner, co-location, Chennai-open).

## Naming

- Files & modules: `snake_case.py`. Test files: `test_<module>.py`.
- Functions & variables: `snake_case`. Classes & Pydantic models: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`. Ports: noun + role (`ProfileParser`, `LLMReasoner`).
- Adapters: named for the technology they wrap (`milvus_index.py`, `dspy_openrouter.py`) so
  swapping an implementation is obvious.
- See `.claude/principles/clean-code.md`: intention-revealing names, functions <20 lines doing one
  thing, <=3 parameters, avoid >3 nesting levels, no dead/commented-out code.

## Testing (`.claude/principles/testing-principles.md`)

- One clear assertion per test; Arrange-Act-Assert; descriptive names stating scenario +
  outcome (e.g. `no_viable_match_returns_zero_eligible`). Tests are independent and order-free.
- **Test pyramid:** many unit tests > fewer integration tests > minimal e2e. Test doubles only
  for external dependencies — never mock domain logic.
- **Contract tests** (`tests/contract/`): one suite per port, written from the spec **before**
  the adapter (`.claude/commands/specify.md`, SDD foundations Rule 2). Every adapter for a port must
  pass that port's suite; a fake satisfying the suite is a legitimate integration double. Prefer
  contract tests over ad-hoc mocking of external services.
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

## Error handling & logging (`.claude/principles/code-quality.md`)

- **No silent failures.** Catch *specific* exceptions, never the base class except in a top-level
  handler. Never log-and-rethrow. Add context via typed `StaffeerError` subclasses at boundaries.
- When the system cannot satisfy a requirement, it **explains the gap** (missing skill, location
  conflict, no availability) rather than fabricating or silently dropping a match.
- Validate all external input (xlsx, PDF, env) at the adapter boundary with Pydantic; fail loudly.
- **Structured logging only:** flat key-value pairs (role id, consultant id, stage), consistent
  keys/units, no prose storytelling. One config in `config.py`; no `print` outside the CLI layer.
- Log LLM calls (model, tokens, latency) and PII-scrubbing actions for auditability.

## Security & governance (`.claude/principles/security.md`)

- Secrets (OpenRouter key) come from `.env` only; `.env` is git-ignored. Never commit keys.
- Validate/sanitize input at every boundary; reject malformed data. Never log PII, tokens, or keys.
- Run `PIIScrubber` (Presidio + spaCy) on profile/feedback text before it reaches the LLM.
- Raw data in `planning/raw-data/` is git-ignored and must stay that way.

## Architecture documentation (`.claude/rules/likec4.md`)

- **LikeC4 is canonical:** model + views live in `docs/architecture/*.c4` with a
  `likec4.config.json` at repo root. Every element carries business-meaningful descriptions and
  source metadata; tags are `UPPER_CASE`; technology strings are specific (`python`, `Typer`,
  `Milvus Lite`); single quotes for values; naming is kebab-case throughout.
- `docs/architecture/L1-system-context.md` and `L2-containers.md` hold rendered **Mermaid**
  mirrors for quick reading; keep them in sync with the `.c4` model when the architecture changes.

## Git & task workflow

The git conventions (Conventional Commits, branch `type/desc` off `main`, small PRs, CI green),
the task execution loop (spec → contract test → simplest impl → quality gates → review → mark →
commit), and the resumable-checklist states (`[ ]`/`[~]`/`[x]`) are canonical in `CLAUDE.md` →
**Development workflow** (and the **Git workflow** subsection). Spec authoring is owned by
`.claude/commands/specify.md`. This page does not restate them.

## SOLID & clean code

`.claude/principles/solid-principles.md` (SRP; depend on abstractions; <=5 deps per class; shallow
hierarchies; dependency injection) and `.claude/principles/clean-code.md` apply to all production code.

## Applicable files (index)

| Concern | File |
|---|---|
| Architecture / ports & adapters | `.claude/principles/hexagonal-architecture.md` |
| Domain modelling | `.claude/principles/domain-driven-design.md` |
| OO design | `.claude/principles/solid-principles.md` |
| Readability | `.claude/principles/clean-code.md` |
| Errors & logging | `.claude/principles/code-quality.md` |
| Tests | `.claude/principles/testing-principles.md` |
| Security | `.claude/principles/security.md` |
| HTTP/API (future web adapter) | `.claude/principles/api-design.md` |
| System quality attributes (NFRs) | `.claude/principles/system-nfrs.md` |
| Diagrams | `.claude/rules/likec4.md` |
| Spec-driven development | `.claude/commands/specify.md` |
| Git, task execution, checklists | `CLAUDE.md` → Development workflow |
