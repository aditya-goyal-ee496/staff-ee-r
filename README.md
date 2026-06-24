# Staffeer — Demand-Supply Matcher

> Given an open consulting role, recommend a **ranked, explainable shortlist** of consultants
> to staff onto it — surfacing the trade-offs for a human to decide.

Staffeer serves **Parity Partners**, a fast-growing consultancy (~5%/month headcount) where a
staffing manager today matches supply (people on the beach, rolling off, or joining) to demand
(dynamic open roles) by hand in a spreadsheet. Staffeer replaces slow, inconsistent manual
judgment with a transparent, repeatable marketplace — without removing the human from the
final decision.

**Status:** POC, built eval-first and vertically sliced. First slice: single role vs.
**beach-only** consultants on hard constraints (location, start date).

## Control plane

This repo is governed by a control plane that loads into every AI-assisted session. It is split
into **Claude-operational** material under `.claude/` and **domain context** under `docs/`:

- **[`CLAUDE.md`](CLAUDE.md)** — entry point: system context, architecture, the binding
  Development workflow (spec-driven dev, task execution, git conventions).
- **[`.claude/principles/`](.claude/principles/)** — binding engineering principles (`RULE-xxx`):
  hexagonal, DDD, SOLID, clean-code, code-quality, testing, security, API design; plus 12-factor,
  production components, system design, and the system NFRs (`system-nfrs.md`).
- **[`.claude/rules/`](.claude/rules/)** — actionable how-to guidelines (`likec4.md`).
- **[`.claude/commands/`](.claude/commands/)** — slash commands (`/clarify`, `/breakdown`,
  `/specify`, `/build-feature`, `/orchestrate`).
- **[`.claude/orchestration/`](.claude/orchestration/)** — the multi-agent orchestration layer.
- **[`docs/conventions.md`](docs/conventions.md)** — development standards (summary + pointers).
- **[`docs/architecture/`](docs/architecture/)** — LikeC4 model (canonical) + Mermaid mirrors.
- **[`docs/adr/`](docs/adr/)** — architecture decision records.
- **[`docs/tasks/`](docs/tasks/)** — the task-level build plan (start at
  [`00-build-plan.md`](docs/tasks/00-build-plan.md)).

**Documentation map.** `.claude/` is what Claude operationally uses — *how* to build (principles,
how-to rules, commands, orchestration). `docs/` is domain context — *what* we're building and
*why* (architecture, decisions, the task plan, conventions). `CLAUDE.md` is the always-loaded
entry point that ties the two together.

## How it works

Ports & adapters (hexagonal): a pure, deterministic **domain core** is isolated behind
**ports**; **adapters** plug into them; the **CLI** and **eval harness** drive the core.

```
ingest -> scrub PII -> enrich/index -> filter (hard constraints) -> score -> rank -> explain
```

Hard constraints (location, start date) are deterministic and repeatable. Soft judgment (skill
fit, adjacency, feedback weighting) may use the LLM — with its reasoning always surfaced.

## Tech stack

Python 3.12 · uv · mise · Pydantic · DSPy (over OpenRouter, or a local model) · Docling ·
Presidio + spaCy · Milvus Lite · Promptfoo + DeepEval.

## Getting started

```bash
make install                 # uv sync
cp .env.example .env          # add OPENROUTER_API_KEY (needed only for the LLM slice)
make test                     # unit + integration tests
make eval                     # deterministic hard-constraint scenarios (must be 100% green)
```

Raw data lives in `planning/raw-data/` (git-ignored): 50 profile PDFs, per-consultant
feedback markdown, and `demand-supply.xlsx` (Beach / Rolling Off / New Joiners / Open Roles).

## Running the matcher (beach-only slice)

The CLI reads the workbook from `--data` or the `STAFFEER_DATA` environment variable. Point it
at the real workbook once, then list roles and match against them:

```bash
export STAFFEER_DATA=planning/raw-data/demand-supply.xlsx

uv run staffeer roles                       # list the open roles in the workbook
uv run staffeer match ROLE-02               # ranked, explained beach shortlist for a role
uv run staffeer match ROLE-02 --show-excluded   # also show who was excluded, and why

# Or point at a workbook explicitly, without exporting the env var:
uv run staffeer match ROLE-01 --data planning/raw-data/demand-supply.xlsx

# The Makefile target wraps `staffeer match` (uses $STAFFEER_DATA):
make match ROLE="ROLE-02"
```

Each consultant comes with the *why* — the rule behind every line is surfaced:

```text
Role ROLE-02: Platform / SRE Engineer — Chennai
1. Karan Mehta (Lead Consultant, Bengaluru) — score 0.75
     - location: Bengaluru satisfies Chennai co-located team (Chennai-based or Chennai-open)
     - availability: available 2026-06-01 is by latest-acceptable 2026-06-22 (start 2026-06-15 + 7d buffer)
     - skills: 3 exact, 0 adjacent, 1 missing of 4 required skills
```

Free-text roles ("backend engineer with database experience") arrive with the LLM slice; until
then `match` takes a sheet role id (`staffeer roles` lists them).

## Development workflow

Plan-first and approval-gated (canonical in [`CLAUDE.md`](CLAUDE.md) → **Development workflow**):

1. Pick the next unblocked task from a `docs/tasks/*.md` checklist; mark it `[~]`.
2. Spec first if it changes a contract — author + approve the spec via **`/specify`** before code.
3. Implement the simplest thing that meets its acceptance criteria.
4. `make format && make test && make lint` (all green).
5. **Request review, wait for approval.**
6. Mark `[x]`; commit with Conventional Commits on a `feat/<slice>` branch via PR.

Refine vague ideas with **`/clarify`** and decompose epics with **`/breakdown`**. Command and
workflow definitions live in [`.claude/commands/`](.claude/commands/) and
[`.claude/orchestration/`](.claude/orchestration/).

## Architecture diagrams (LikeC4)

The architecture is modelled canonically in **LikeC4** (`docs/architecture/*.c4`, project config
`likec4.config.json`); [`L1-system-context.md`](docs/architecture/L1-system-context.md) and
[`L2-containers.md`](docs/architecture/L2-containers.md) carry rendered **Mermaid** mirrors for
quick reading. Authoring rules: [`.claude/rules/likec4.md`](.claude/rules/likec4.md).

To explore the model interactively (requires Node):

```bash
make arch                              # interactive viewer (wraps `npx likec4 start`)
npx likec4 start                       # same, directly
npx likec4 export png -o docs/architecture/   # render static images
npx likec4 build                       # build a browsable static site
```

## Repository layout

```
CLAUDE.md            control-plane entry point
Makefile             build / test / eval / run targets
likec4.config.json   LikeC4 project config
.claude/             control plane: principles, rules, commands, orchestration
src/staffeer/        domain / ports / adapters / cli   (built per docs/tasks/)
tests/               unit + integration
evals/               scenario evals now; Promptfoo + DeepEval later
docs/                domain context: architecture, adr, tasks, conventions
planning/raw-data/   source data (git-ignored)
```

---

## Problem brief & domain guidance

The authoritative brief from the staffing business. The system must honour these.

### Context

A consultancy ("Parity Partners") continually moves consultants between client engagements. On
the supply side, people sit in 3 states: on the beach (free now), rolling off within ~90 days
(free on a date), or joining in the next ~60 days. On the demand side is a list of open roles
that are quite dynamic — each with required skills, a start date, a location constraint, and a
priority. The firm is growing ~5% headcount a month, so bench, joiners, and open roles are in
constant flux; today's snapshot is a fraction of what this must handle. Today a staffing
manager matches the two by hand in a spreadsheet on judgment. It's slow and inconsistent.

**Task:** given an open role, recommend a ranked, explainable shortlist of consultants to staff
onto it, surfacing the trade-offs for a human to decide.

### Current manual process

- Weekly forum with HOEs, EMs, staffers, and leadership reviews opportunities.
- Not simple skill matching — involves client context, team dynamics, stakeholder preferences
  (e.g. an "AI architect" role actually needs a tech lead who understands AI in the SDLC).
- Considers relationship factors (some stakeholders micromanage, some prefer autonomy).
- Evaluates feedback: project performance, client feedback, beach performance.
- Sometimes matches adjacent skills (Python needed but only Java devs available — check
  willingness to learn).

**System goal:** a democratic demand-supply marketplace that removes human bias while forming
high-performing teams.

### Domain rules

- **Location**: hard requirement — no relocation assumptions; co-location flag indicates the
  team must be in a specific city (e.g. MNS/BCG Chennai teams).
- **Start date flexibility**: a few days' buffer acceptable for roll-offs/new joiners, not months.
- **Priority framework**: location currently highest priority, but teams may implement a
  different weighting if justified.
- **System scope**: focus on the matching algorithm, not UI; CLI is sufficient.
- **Roll-off dates** in the sheet are final (30-day notice already incorporated where applicable).
- **Multiple roles**: start with single-role matching; multi-role team formation is optional.
- **Evaluation**: 100% accuracy is neither expected nor desired (it signals insufficient test
  coverage); the system should handle uncertainty.

### Feedback notes

- New joiners have unverified skills in the EE context.
- Project feedback exists as client feedback (may be one-dimensional) and internal EE feedback
  (more comprehensive on team fit and hands-on ability).
- Beach feedback shows performance trajectory (improved / maintained / decreased).
- Teams decide weighting between skill claims, project feedback, and beach performance.

### Skills matching

- Hard skills may have acceptable alternatives (a Kotlin requirement may accept a Java dev
  willing to learn).
- Additional data available: project feedback, client feedback — teams decide if/how to use.
- The system should explain gaps when it cannot match requirements.

### Development philosophy

- Embrace uncertainty — don't try to answer everything on day one.
- Build an extensible system where priorities/weights can change.
- Vertical slicing: start with beach-only matching, add variables incrementally.
- POC approach: explore with business, build a first version, iterate.
- Prioritise the top 10-20 backlog items, not a full thousand-item list.

### API keys & tech stack

- Use the OpenRouter API keys provided; local model execution is also acceptable.
- A tech stack is pre-configured on machines; teams may use alternatives if justified.

### UX

- Minimum: a CLI accepting a single requirement ("backend engineer with database experience").
- Optional: web interface, file upload for multiple roles, team-formation queries.
- Focus on system logic, not UX polish. Order of consumers: tests/evals, then CLI, then web.

### Evals

- Include negative scenarios, not just positive cases.
- Find negative examples in the dataset or create synthetic data.
- A 100%-success eval is considered a failure — it signals insufficient exploration.
- Non-deterministic systems cannot achieve perfect accuracy; balance thoroughness with constraints.

### Guiding principles for the system

These quality attributes (NFRs) are also captured for the build system in
[`.claude/principles/system-nfrs.md`](.claude/principles/system-nfrs.md) — keep the two in sync.

- **Accurate & Relevant** — is it correct, and did it answer what was actually asked?
  Track-based systems (e.g. policy bots) have ground truth, so accuracy is measurable;
  open-ended systems lean on relevancy, scored by an LLM-as-judge and backed by user behaviour.
- **Repeatable & Predictable** — variance isn't always bad. In regulated/high-stakes contexts
  inconsistency is a trust failure; in creative/open-ended ones it's desirable. The job is to
  decide, deliberately, *where* variance is allowed.
- **Explainable & Referenceable** — the system can show its reasoning (explainability) and trace
  each output back to a specific, verifiable source (referenceability).
- **Secure & Governed** — access, data exposure, and the decisions it may make stay inside set
  limits; plan for the breach and for bowing out of a conversation cleanly.
- **Effective & Efficient** — fast and cheap means nothing if the user's problem isn't solved;
  watch hidden costs (work that looks efficient but needs heavy manual rework).
- **Reputation & Ethics** — a single AI mistake can do lasting brand damage; the harness must
  spell out brand values, regulatory obligations, and ethical lines, and hold the system to them.
