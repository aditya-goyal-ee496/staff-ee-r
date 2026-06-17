# Staffeer — Demand-Supply Matcher

Given an open consulting role, Staffeer recommends a **ranked, explainable shortlist** of
consultants to staff onto it, surfacing the trade-offs for a human to decide. It serves
"Parity Partners", a fast-growing consultancy (~5%/month headcount) where a staffing manager
currently matches supply (people on the beach, rolling off, or joining) to demand (dynamic
open roles) by hand in a spreadsheet. The system replaces slow, inconsistent manual judgment
with a transparent, repeatable marketplace — without pretending to remove the human from the
final decision.

This is a **POC**, built eval-first and vertically sliced. The first slice matches a single
role against **beach-only** consultants; roll-offs, new joiners, and multi-role team formation
come later. The full task-level plan is in `docs/tasks/` (start at `docs/tasks/00-build-plan.md`).

## Core principles

1. **Explainable over clever.** Every recommendation states *why* a consultant ranked where
   they did, *which source* backs each claim, and *what gaps* remain. An unexplained match is
   a bug, not a feature.
2. **Decide where variance is allowed.** Hard constraints (location, start date) are
   deterministic and repeatable. Soft judgment (fit, adjacent skills, feedback weighting) may
   use the LLM — but its reasoning is surfaced, never hidden.
3. **Eval-first, embrace uncertainty.** Tests and evals are the first consumers, before the
   CLI. 100% eval accuracy is treated as a failure signal (insufficient coverage), and
   negative scenarios are mandatory.
4. **Extensible by design.** Priorities and weights change. Scoring, weighting, and supply
   states are pluggable so the business can re-tune without a rewrite.
5. **Secure & governed.** PII is scrubbed before it reaches an LLM. The system bows out and
   explains gaps rather than fabricating a match.

## Architecture overview

Ports & adapters (hexagonal). A pure, deterministic **domain core** is isolated from all I/O
behind **ports** (interfaces); concrete **adapters** plug into those ports; **driving
adapters** (CLI, eval harness) call the core.

```
Driving adapters -> Domain core (ports) <- Driven adapters
  CLI, evals          matching/scoring      Docling, xlsx, Milvus,
                      ranking, explain      DSPy/OpenRouter, Presidio
```

- **Domain core** (`src/staffeer/domain/`): Pydantic models (`Consultant`, `Role`,
  `SupplyState`, `Match`), constraint filtering, scoring, ranking, explanation assembly.
  Pure Python, no I/O, fully unit-testable.
- **Ports** (`src/staffeer/ports/`): `ProfileParser`, `FeedbackStore`, `SupplyDemandSource`,
  `SemanticIndex`, `LLMReasoner`, `PIIScrubber`.
- **Adapters** (`src/staffeer/adapters/`): Docling profile parser, xlsx supply/demand loader,
  markdown feedback loader, Milvus Lite semantic index, DSPy+OpenRouter reasoner, Presidio +
  spaCy PII scrubber.
- **Entry points** (`src/staffeer/cli/`, `evals/`): Typer CLI accepting a free-text role
  ("backend engineer with database experience"); Promptfoo + DeepEval suites.

The matching pipeline within the core: **ingest -> scrub PII -> enrich/index -> filter (hard
constraints) -> score (skills + feedback + availability) -> rank -> explain.**

Architecture is modelled canonically in **LikeC4** (`docs/architecture/*.c4`, see
`docs/rules/likec4.md`); `docs/architecture/L1-*.md` and `L2-*.md` carry rendered Mermaid
mirrors for quick reading. See `docs/conventions.md` for standards and `docs/adr/` for decisions.

## Engineering rules (binding)

Code and reviews must follow the rule files in `docs/rules/` (each has concrete `RULE-xxx`
directives). When a concern arises, the matching file is authoritative:

- `docs/rules/hexagonal-architecture.md` — ports/adapters, dependency rule, error mapping.
- `docs/rules/domain-driven-design.md` — entities, value objects, aggregates, ubiquitous language.
- `docs/rules/solid-principles.md` — SRP, dependency inversion, interface segregation.
- `docs/rules/clean-code.md` — small functions (<20 lines), intention-revealing names, no dead code.
- `docs/rules/code-quality.md` — specific error handling, structured logging only.
- `docs/rules/testing-principles.md` — one assertion/test, AAA, descriptive names, test pyramid.
- `docs/rules/security.md` — secrets in env, validate input at boundaries, never log PII/secrets.
- `docs/rules/api-design.md` — REST conventions (for any future web/API adapter).
- `docs/rules/git-rules.md` — Conventional Commits, PR-only, CI must pass.
- `docs/rules/task-execution.md` + `docs/rules/long-running-tasks.md` — the workflow below.

Guiding principles: `docs/principles/` (12-factor, production components, system design).

## Development workflow

1. Pick the next unblocked task from the relevant `docs/tasks/*.md` checklist; mark it `[~]`.
2. Implement the **simplest** thing that satisfies its acceptance criteria.
3. Run quality gates: `make format`, `make test`, `make lint` (all must pass).
4. **Request review and wait for explicit approval** before marking done (`task-execution.md`).
5. Mark the task `[x]`, then commit per `git-rules.md` (Conventional Commits, e.g.
   `feat(matching): add beach-only constraint filter`, on a `feat/<slice>` branch via PR).

Track multi-stage work as `docs/tasks/*.md` checklists (`[ ]` todo, `[~]` in progress, `[x]`
done) — detailed enough to resume cold. Refine vague ideas with `/clarify`; decompose epics
with `/breakdown` (definitions in `docs/commands/`, installed in `.claude/commands/`).

## Tech stack

- **Python 3.12**, **uv** (deps/venv), **mise** (toolchain).
- **Pydantic** — domain models and validation.
- **DSPy** — LLM orchestration and prompt optimization, over **OpenRouter** (key in `.env`;
  local model execution also acceptable).
- **Docling** — parse consultant profile PDFs (some templated, some free-form).
- **Presidio + spaCy** — detect/scrub sensitive data before LLM calls.
- **Milvus Lite** — vector storage and semantic retrieval over skills/profiles.
- **Promptfoo + DeepEval** — LLM evaluation, testing, and quality engineering.

## Data

Raw inputs live in `planning/raw-data/` (git-ignored):
- `profiles/` — 50 consultant profile PDFs.
- `project_feedback/` — per-consultant project/client feedback (markdown).
- `demand-supply.xlsx` — supply tabs (Beach / Rolling Off / New Joiners) and Open Roles.

## Domain rules (binding)

- **Location** is a hard constraint — no relocation assumptions; the co-location flag means the
  team must be physically in a specific city. `Chennai-open` is the structured signal for
  Chennai-co-located teams.
- **Start date**: a few days' buffer is acceptable for roll-offs/new joiners; months are not.
- **Priority**: location is currently weighted highest, but weights are configurable if justified.
- **Roll-off dates** in the sheet are final (30-day notice already incorporated).
- **Feedback** comes as client feedback (may be one-dimensional) and internal EE feedback
  (richer on team fit / hands-on ability); beach feedback shows trajectory. New joiners have
  **unverified** skills. Teams decide the weighting and must justify it.
- **Adjacent skills** may be acceptable (e.g. a Java dev for a Kotlin role, willing to learn) —
  the system must explain the substitution.

## Commands

```bash
make install   # uv sync — install deps into the project venv
make test      # run unit + integration tests (pytest)
make eval      # run eval suites (deterministic scenarios now; Promptfoo + DeepEval later)
make lint      # ruff check + ruff format --check + mypy
make format    # ruff format + ruff check --fix
make match     # run the CLI against a role, e.g. make match ROLE="ROLE-01"
```
