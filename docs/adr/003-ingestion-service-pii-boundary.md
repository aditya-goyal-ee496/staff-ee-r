# ADR-003: Introduce IngestionService as a named domain-core boundary for PII-scrubbing

## Status: Accepted

## Context

Slice 04 activates three driven adapters behind existing frozen ports (`ProfileParser`,
`FeedbackStore`, `PIIScrubber`) and adds additive fields to their value objects
(`skills_verified` on `ParsedProfile`, `beach_notes` on `Feedback`). Adding the adapters
alone was sufficient to pass the acceptance criteria, but left the PII-scrubbing obligation
enforced only by a runtime guard in `build_matcher` and a comment in `composition.py`.

The security principle (`.claude/principles/security.md`) and invariant I14 both state that
all profile and feedback text **must** pass through `PIIScrubber` before reaching any LLM or
semantic index. With no named seam in the domain, that invariant was a convention rather than
a code structure — a future caller that bypassed the composition root would have no obvious
signal that scrubbing was required.

Two approaches were considered:

1. **Convention + composition guard only** — keep `build_matcher`'s fail-closed guard and
   rely on convention that callers must use it. Simpler, no new class.
2. **Named `IngestionService` in the domain core** — a pure orchestrating service that
   composes `ProfileParser + FeedbackStore + PIIScrubber` and makes scrubbing structurally
   mandatory on every code path that touches profile/feedback text.

## Decision

Introduce **`IngestionService`** (`src/staffeer/domain/ingestion.py`) as a named, pure-domain
application service within the domain core.

- It depends only on `staffeer.ports.*` (no I/O, no adapters, no third-party imports).
- It provides `ingest_profile(path)` and `ingest_feedback(consultant_id)`, each of which
  returns both the structured data and the `ScrubbedText`. Callers receive scrubbed text as
  the only text surface — they cannot accidentally use the raw text without extra effort.
- The service is **not yet wired into `Matcher`**; it is a standalone domain utility for now.
  Integration into the matching pipeline is deferred to a future slice, once the pipeline
  is extended to consume enriched profile/feedback data.
- `build_matcher`'s fail-closed guard is retained as defence-in-depth at the composition root.
- **Presidio is now the default on the LLM/semantic path.** `_build_pii_scrubber` in
  `composition.py` returns `PresidioPIIScrubber()` when `config.llm_enabled or
  config.semantic_enabled` (else `NullPIIScrubber()`). The `build_matcher`
  `isinstance(pii, NullPIIScrubber)` guard is kept as defence-in-depth — it is now unreachable
  through normal config but still protects any path that injects a null scrubber.

## Consequences

**Good**
- The PII-scrubbing obligation is a code structure, not a convention: `IngestionService` is
  the only sanctioned way to obtain text from profiles or feedback in the domain, and it always
  returns `ScrubbedText`. A future developer cannot accidentally get raw text without bypassing
  an explicit named service.
- The service is unit-testable in isolation (stub ports, no I/O) and its invariant (scrubbing
  always occurs) is expressed directly as a contract test.
- The LikeC4 model can now name `IngestionService` as a component within `staffeer.core`,
  making the ingestion pipeline visible in the architecture diagram alongside filter/score/
  rank/explain.

**Costs / trade-offs**
- A small amount of indirection: callers must obtain an `IngestionService` instance rather
  than calling ports directly. Mitigated by the service being minimal (two methods, no state
  beyond injected ports).
- `IngestionService` is currently unused by `Matcher` — it exists as a domain utility. Until
  it is wired into the pipeline it adds surface area without active use. Accepted because the
  boundary is the point: establishing the seam now is cheaper than retrofitting it later.

## LikeC4 update required

`docs/architecture/model.staffeer.c4` must add an `ingestion-service` component under
`staffeer.core` and a relationship from `ingestion-service` to `staffeer.ports`, to reflect
that the domain core now contains an explicit ingestion + PII-scrub boundary.

## Follow-ups

- **Pipeline integration** — wire `IngestionService` into `Matcher` when the matching
  pipeline is extended to consume parsed profiles and scrubbed feedback text (a future slice).
