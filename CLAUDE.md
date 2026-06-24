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
`.claude/rules/likec4.md`); `docs/architecture/L1-*.md` and `L2-*.md` carry rendered Mermaid
mirrors for quick reading. See `docs/conventions.md` for standards and `docs/adr/` for decisions.

## Engineering principles & rules (binding)

The control plane lives under `.claude/`, split by purpose:

- **`.claude/principles/`** — the binding engineering principles to follow when writing code
  (each has concrete `RULE-xxx` directives). When a concern arises, the matching file is
  authoritative:
  - `hexagonal-architecture.md` — ports/adapters, dependency rule, error mapping.
  - `domain-driven-design.md` — entities, value objects, aggregates, ubiquitous language.
  - `solid-principles.md` — SRP, dependency inversion, interface segregation.
  - `clean-code.md` — small functions (<20 lines), intention-revealing names, no dead code.
  - `code-quality.md` — specific error handling, structured logging only.
  - `testing-principles.md` — one assertion/test, AAA, descriptive names, test pyramid.
  - `security.md` — secrets in env, validate input at boundaries, never log PII/secrets.
  - `api-design.md` — REST conventions (for any future web/API adapter).
  - `system-nfrs.md` — the system's quality attributes (accurate, repeatable, explainable,
    secure, efficient, ethical) the matcher is held to.
  - `12-factor-app.md`, `essential-components-production-web-app.md`, `system-design.md` —
    production/system guidance.
- **`.claude/rules/`** — actionable how-to guidelines referenced while working:
  - `likec4.md` — how to author the LikeC4 architecture model and keep its Mermaid mirrors in sync.
- **`.claude/commands/`** — slash-command definitions (`/clarify`, `/breakdown`, `/specify`,
  `/build-feature`, `/orchestrate`).
- **`.claude/orchestration/`** — the orchestration layer (workflow contract, model-usage, ledger,
  workflows).

The process workflow itself (spec-driven development, task execution, resumable checklists, and
git conventions) is described below — it is owned by the **Development workflow** section and the
`/specify` / `/build-feature` / `/orchestrate` workflows, not by separate rule files.

## Development workflow

The execution loop for one task:

1. Pick the next unblocked task from the relevant `docs/tasks/*.md` checklist; mark it `[~]`.
2. **Spec first (SDD).** If the task introduces or changes a contract (a port, a domain value
   object, or a pure-function group), author/confirm its **spec** and **get the spec approved
   before writing implementation code** — use `/specify`. The spec is the source of truth; the
   contract test is the spec made executable; the implementation is whatever makes it pass.
   Skip only when the task is purely additive against an already-approved, frozen contract.
3. Write the contract/unit test from the spec first (it must fail before implementation exists).
4. Implement the **simplest** thing that satisfies the acceptance criteria.
5. Run quality gates: `make format`, `make test`, `make lint` (all must pass).
6. **Request review and wait for explicit approval** before marking done.
7. Mark the task `[x]`, then commit (see **Git workflow** below).

**Resumable checklists.** Track multi-stage work as `docs/tasks/*.md` markdown checklists with
states `[ ]` not started, `[~]` in progress (update the item in place; add subtasks/detail under
it), `[x]` done. Each checklist must carry enough detail to resume with empty context. Refine
vague ideas with `/clarify`; decompose epics with `/breakdown`.

**Spec discipline.** A frozen, approved contract is what lets independent tracks run in parallel —
never change one silently; **amend the spec first**, then the contract test, then the code, and
prefer additive change (a defaulted field, a new `ScoreContribution`) over reshaping a frozen
record. See `.claude/commands/specify.md` for the full spec format and contract-test rules.

### Git workflow

- **Conventional Commits:** `type(scope): description` — types `feat|fix|chore|docs|refactor|test|ci`;
  imperative present tense; subject <72 chars; body explains *why*; reference the work item
  (`Refs: docs/tasks/02-beach-matching.md`).
- **Atomic commits:** each commit compiles, passes tests, and is independently revertable.
- **Branches:** `type/short-description` (e.g. `feat/beach-matching`) off `main`; never commit
  directly to `main`.
- **PRs:** small (reviewable in <30 min), squash WIP/fixup, describe what/why/how-to-test, delete
  the branch after merge. All CI checks (lint + test) must pass; PRs touching scoring/prompts must
  show eval results.

### Automating the loop

Use the orchestration layer (`.claude/orchestration/`): `/build-feature <task-file> [mode]` runs
the **build-feature** workflow (spec → decompose → eval-first tests → implement → quality → verify
→ architecture/ADR → progress report → finalize), spawning one sub-agent per atomic instruction
under the model-usage guideline (Opus orchestrates; Sonnet/Haiku work) and logging every agent to a
per-run JSON ledger. `/orchestrate [workflow] [input] [mode]` is the generic, workflow-agnostic
manager for that and any future workflow. Default mode `gate` honours every approval gate (incl.
the spec gate above); `checkpoint`/`autonomous` trade oversight for throughput. Command and
workflow definitions live in `.claude/commands/` and `.claude/orchestration/`.

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
make arch      # open the LikeC4 diagram viewer (npx likec4 start; requires Node)
```

Orchestration (see `.claude/orchestration/`):
```
/orchestrate [workflow] [input] [mode]   # generic manager; lists workflows if no args
/build-feature <task-file> [mode]        # shortcut for /orchestrate build-feature
```
