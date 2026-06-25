# ADR-006: An `IndexBuilder` application service builds the profile-text semantic index

## Status: Accepted

## Context

Slice 05b feeds PII-scrubbed consultant profile text (from PDFs) into the semantic
index alongside the structured xlsx summary, so semantic retrieval analyses what a
consultant actually did, not just their skills list. The `ProfileParser` and
`PIIScrubber` ports already existed; the `MilvusSemanticIndex` adapter and the
`staffeer index` CLI command already existed (from slice I3). This slice wires them
together so the index embeds richer, profile-derived text.

Two questions had to be answered: **how** to scrub, and **where** the orchestration lives.

**Scrubbing.** The acceptance criteria require the **combined** text
(`summary + "\n\n" + parsed.text`) to be scrubbed once as a single concatenated string
before embedding, so no PII from either source escapes. The existing
`IngestionService` (ADR-003) scrubs only the raw profile text in isolation; routing
through it as-is would leave the summary unscrubbed or require an awkward double-scrub,
and extending its frozen contract here would be an unspecified change. ADR-003 explicitly
deferred wiring `IngestionService` into the pipeline.

**Where orchestration lives.** An initial implementation put the parse → scrub → upsert
loop in the `staffeer index` CLI command. Review flagged that this gave the driving
adapter two responsibilities (user I/O *and* index-build orchestration). That was
rejected in favour of a dedicated domain application service.

## Decision

A new domain application service, **`IndexBuilder`** (`src/staffeer/domain/index_builder.py`),
owns the index-build use case. It mirrors `Matcher`'s style: a frozen dataclass that
depends only on **port interfaces** (`ProfileParser`, `PIIScrubber`, `SemanticIndex`) and
pure domain functions, with **no filesystem I/O**.

- `IndexBuilder.build(consultants, profiles_dir, stems) -> list[IndexOutcome]` — per
  consultant: resolve the profile via the pure `profile_match.resolve_profile_stem`
  (filename stem ↔ `consultant.name`), construct the path (pure), build + scrub the text,
  and upsert an `IndexItem` through the `SemanticIndex` port. It returns an `IndexOutcome`
  (`consultant_id`, `profile_attached`) per consultant.
- `_text_for(...)` scrubs the **combined** summary + profile text once
  (`pii.scrub(summary + "\n\n" + parsed.text)`), satisfying the PII-before-index invariant
  (I14). On `ProfileParseError` or no matching profile it falls back to the scrubbed
  summary alone — never fabricated or another consultant's text (Principle 5).

The `staffeer index` CLI command is now **thin**: it builds the matcher, performs the one
piece of genuine I/O that must live in the driving adapter — globbing `*.pdf` stems from
`profiles_dir` — constructs an `IndexBuilder` from the matcher's ports, calls `build(...)`,
and prints `indexed: <id> (profile-attached|summary-only)` per outcome. It never imports
or instantiates adapters; the dependency rule holds.

`IngestionService` is unchanged and remains the sanctioned utility for future pipeline
integration.

## Consequences

**Good**
- Index-build orchestration lives in the domain core as a single-responsibility
  application service, unit-testable with stub ports; the CLI is a thin driving adapter
  again (its only index-specific job is the directory glob and printing).
- The combined-text scrub requirement is met with one `pii.scrub()` call — no partial-scrub
  risk.
- The dependency rule is respected: `IndexBuilder` and `profile_match` touch only ports and
  pure functions; the CLI touches only `Matcher`, ports, and the new service. CI stays green
  without Docling (stub `ProfileParser` + in-memory fake `SemanticIndex` in tests).

**Costs / trade-offs**
- A second application service (`IndexBuilder`) now sits alongside `Matcher`. This is the
  intended SRP split, but both aggregate overlapping ports; a future consolidation could
  share a common port bundle.
- `IngestionService` remains not wired into the active pipeline. The follow-up below still
  stands.

## LikeC4 impact

Because orchestration is in the core (not the CLI), the existing container relationships
already represent the index-build flow: `cli -> core` (build) → `core -> ports`
(`SemanticIndex`) ← `adapters -> ports`, with `adapters -> index 'writes / queries
embeddings'`. No new container relationship is required. For fidelity an **`Index Builder`
component** was added to the `core` container in `model.staffeer.c4` and the `cli -> core`
label broadened to "matching pipeline + index build". The L2 container Mermaid mirror is
unchanged (container-level relationships are unaffected).

## Follow-ups

- **Pipeline integration** — unify scrubbing paths so `IndexBuilder` and a future
  `IngestionService`-based pipeline share a combined-scrub API, removing the deferred-service
  divergence noted in ADR-003.
- **Profile → consultant join** — replace best-effort filename matching with a deterministic
  `consultant.id` ↔ file map when profile filenames are standardised.
