# L2 — Containers

> **Canonical model:** the architecture is defined in LikeC4 at `docs/architecture/model.staffeer.c4` (views `context` / `containers`). The Mermaid diagram below is a rendered mirror — keep it in sync with the `.c4` model when the architecture changes (see `.claude/rules/likec4.md`).


Staffeer is a single Python application (a CLI plus an eval harness), not a distributed
system. The "containers" here are the deployable/runnable units and the major internal
boundaries that matter for how the code is organized and tested.

## Runnable units

- **CLI (`staffeer` / `src/staffeer/cli/`)** — Typer app. Driving adapter. Accepts a free-text
  role (`"backend engineer with database experience"`) or a role id from the sheet, invokes
  the domain core, and renders the ranked, explained shortlist to the terminal.
- **Eval harness (`evals/`)** — Promptfoo + DeepEval. The *first* consumer. Drives the same
  core with curated datasets (including negative cases) and scores relevance/faithfulness.

## Internal boundaries (hexagonal)

- **Domain core (`src/staffeer/domain/`)** — pure, deterministic. Models, hard-constraint
  filtering, scoring, ranking, explanation assembly. No I/O, no third-party clients.
- **Ports (`src/staffeer/ports/`)** — the interfaces the core depends on: `ProfileParser`,
  `FeedbackStore`, `SupplyDemandSource`, `SemanticIndex`, `LLMReasoner`, `PIIScrubber`.
- **Driven adapters (`src/staffeer/adapters/`)** — concrete implementations:
  - Docling → parse profile PDFs
  - openpyxl/pandas → load `demand-supply.xlsx`
  - markdown loader → project feedback
  - Presidio + spaCy → PII scrubbing (runs before any LLM call)
  - Milvus Lite → embed + semantically retrieve over skills/profiles
  - DSPy over OpenRouter (or local model) → soft-judgment reasoning

## Pipeline

`ingest → scrub PII → enrich/index → filter (hard constraints) → score → rank → explain`

The first vertical slice runs this against **beach-only** supply. Hard constraints (location,
start date) are deterministic; scoring soft factors (skills incl. adjacency, feedback,
availability) may call the LLM, with all reasoning surfaced for explainability.

## Diagram

```mermaid
C4Container
    title Containers — Staffeer

    Person(sm, "Staffing Manager", "Submits role, reads shortlist")

    System_Boundary(s, "Staffeer") {
        Container(cli, "CLI", "Python / Typer", "Driving adapter: takes a role, prints ranked shortlist + rationale")
        Container(evals, "Eval Harness", "Promptfoo + DeepEval", "First consumer: scenario + metric evaluation")
        Container(core, "Domain Core", "Python / Pydantic", "Filter, score, rank, explain — pure & deterministic")
        Container(ports, "Ports", "Python Protocols", "ProfileParser, FeedbackStore, SupplyDemandSource, SemanticIndex, LLMReasoner, PIIScrubber")
        Container(adapters, "Driven Adapters", "Python", "Docling, xlsx, markdown, Presidio, Milvus, DSPy")
        ContainerDb(index, "Semantic Index", "Milvus Lite", "Embeddings over skills/profiles")
    }

    System_Ext(files, "Raw Data", "PDF / md / xlsx (git-ignored)")
    System_Ext(llm, "OpenRouter / Local LLM", "Soft-judgment reasoning")

    Rel(sm, cli, "role in / shortlist out")
    Rel(cli, core, "invokes")
    Rel(evals, core, "drives with datasets")
    Rel(core, ports, "depends on (interfaces)")
    Rel(adapters, ports, "implements")
    Rel(adapters, files, "parses / loads")
    Rel(adapters, index, "writes / queries")
    Rel(adapters, llm, "reasons over scrubbed text")

    UpdateRelStyle(core, ports, $offsetY="-10")
```
