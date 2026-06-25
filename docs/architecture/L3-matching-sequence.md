# L3 — Matching & Indexing sequences

> **Canonical model:** the static architecture is defined in LikeC4 at
> `docs/architecture/model.staffeer.c4` (views `context` / `containers`); see
> [`L1-system-context.md`](L1-system-context.md) and [`L2-containers.md`](L2-containers.md).
> The dynamic (runtime) sequences below mirror the behaviour of `Matcher` in
> `src/staffeer/domain/matcher.py` and the `index` command in `src/staffeer/cli/main.py` —
> keep them in sync with that code when the pipeline changes (see `.claude/rules/likec4.md`).

These two flows show *how* the hexagonal pieces collaborate at runtime. The domain core (`Matcher`)
only ever calls **ports**; the concrete adapters (Milvus, Presidio, DSPy) sit behind those ports.
PII is scrubbed before any text reaches the semantic index or the LLM.

## 1. Match a role → ranked, explained shortlist

Per eligible consultant, the matcher blends three signals into the score —
**lexical skill coverage** (deterministic), **LLM soft judgment**, and **semantic similarity** —
and surfaces each as an explanation factor. The LLM and semantic ports are wrapped: a port failure
degrades to an abstaining assessment / empty hits rather than aborting the match.

```mermaid
sequenceDiagram
    autonumber
    actor SM as Staffing Manager
    participant CLI as CLI (Typer)
    participant M as Matcher (domain core)
    participant Supply as SupplyDemandSource
    participant Screen as screen_consultants()
    participant PII as PIIScrubber
    participant LLM as LLMReasoner
    participant SI as SemanticIndex
    participant Rank as rank() / assemble_match()

    SM->>CLI: staffeer match "<role>"
    CLI->>M: match(role)
    M->>Supply: consultants(*include_states)
    Supply-->>M: candidates
    M->>Screen: screen_consultants(candidates, role)
    Screen-->>M: EligibilityResult[] (eligible + excluded, with reasons)

    loop for each eligible consultant
        M->>M: skill_coverage(role, consultant) [lexical, deterministic]
        M->>PII: scrub(role description)
        M->>PII: scrub(consultant summary)
        PII-->>M: scrubbed text

        M->>LLM: assess(consultant_summary, role_description)
        alt port raises
            LLM-->>M: (exception) → abstaining SoftAssessment
        else ok
            LLM-->>M: SoftAssessment(score, confidence)
        end

        M->>SI: query(scrubbed_role, namespace="skills", top_k=5)
        alt port raises / index unavailable
            SI-->>M: (exception) → [] (no semantic signal)
        else ok
            SI-->>M: Hit[] (id, score, text)
        end

        M->>Rank: assemble_match(consultant, [skill, soft, semantic] contributions, explanation)
        Rank-->>M: Match (score + factors)
    end

    M->>Rank: rank(matches)
    Rank-->>M: ordered matches
    M-->>CLI: Shortlist(matches, excluded)
    CLI-->>SM: ranked shortlist + per-factor rationale
```

## 2. Build the semantic index (`staffeer index` / `make index`)

`MilvusSemanticIndex` is only wired when `semantic_enabled` **and** `milvus_path` are set;
otherwise the composition root returns `NullSemanticIndex` (with a warning) and this command exits
early. Every consultant summary is PII-scrubbed before it is embedded and upserted; `upsert` is
idempotent on `id`, so re-running the build is safe.

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operator
    participant CLI as CLI (index command)
    participant Comp as composition root
    participant M as Matcher
    participant Supply as SupplyDemandSource
    participant PII as PIIScrubber
    participant SI as MilvusSemanticIndex
    participant Milvus as Milvus Lite + embeddings

    Op->>CLI: make index  (needs STAFFEER_MILVUS_PATH)
    CLI->>CLI: load config (env + optional --data)
    alt milvus_path not set
        CLI-->>Op: error + exit 1
    else configured
        CLI->>Comp: build_matcher(config)
        Comp-->>M: Matcher wired with MilvusSemanticIndex
        CLI->>Supply: consultants(*include_states)
        Supply-->>CLI: consultants
        loop for each consultant
            CLI->>PII: scrub(consultant summary)
            PII-->>CLI: scrubbed text
            CLI->>SI: upsert(IndexItem id, text, namespace="skills", metadata)
            SI->>Milvus: embed(text) → delete existing id → insert vector + meta
            Milvus-->>SI: ok
            CLI-->>Op: progress (consultant indexed)
        end
        CLI-->>Op: "Index built."
    end
```

## Notes

- **Determinism boundary.** Hard-constraint screening (`screen_consultants`) and lexical
  `skill_coverage` are fully deterministic; only the LLM and semantic signals are variable, and
  both are surfaced as explanation factors so a recommendation is never unexplained.
- **Fail-soft soft signals.** A failing `LLMReasoner` or `SemanticIndex` never aborts a match —
  the matcher degrades to an abstaining assessment / empty hits. Adapter-level infrastructure
  errors are mapped to `SemanticIndexError` at the boundary (hexagonal error mapping).
- **PII before embedding/LLM.** Both flows scrub text via `PIIScrubber` before it reaches the
  semantic index or the LLM (Principle 5 — secure & governed).
