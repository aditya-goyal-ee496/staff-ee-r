# ADR-001: Hexagonal, eval-first architecture for the matcher POC

## Status: Accepted

## Context

Staffeer must produce ranked, explainable consultant shortlists for open roles from messy,
fast-changing inputs (mixed-format PDF profiles, markdown feedback, a live xlsx of supply and
demand). The brief is explicit that this is a POC to be built incrementally — start with
beach-only matching and add variables over time — and that **tests and evals are the first
consumers**, before the CLI. It also demands explainability, configurable priority weights,
PII governance before any LLM call, and a deliberate split between where output variance is
acceptable (soft judgment) and where it is not (hard constraints like location and start date).

The pre-selected stack (Python, uv, mise, Docling, Pydantic, DSPy, Presidio/spaCy, Milvus
Lite, Promptfoo/DeepEval, OpenRouter) is varied and several pieces are likely to be swapped as
the POC matures (e.g. LLM provider, vector store). We need a structure that keeps that churn
out of the part of the system that encodes the business rules.

Two structures were considered: a simple layered pipeline (less ceremony), and ports &
adapters / hexagonal (stronger isolation).

## Decision

Adopt **ports & adapters (hexagonal) architecture**, single repository, with an
**eval-first** workflow.

- A pure, deterministic **domain core** (`src/staffeer/domain/`) holds the models and the
  filter → score → rank → explain logic, with **no I/O**.
- All external concerns sit behind **ports** (`ProfileParser`, `FeedbackStore`,
  `SupplyDemandSource`, `SemanticIndex`, `LLMReasoner`, `PIIScrubber`) implemented by
  swappable **adapters**.
- The dependency rule points inward: `domain/` never imports adapters or third-party I/O.
- The CLI and the eval harness are driving adapters; the eval harness is treated as the
  primary consumer, with mandatory negative scenarios and 100% pass rates treated as a
  coverage warning.
- Build in vertical slices, starting with **beach-only** matching.

## Consequences

**Good**
- Business rules (location/date constraints, scoring, explanation) are unit-testable in
  isolation, deterministically — directly supporting the "repeatable where it matters" and
  explainability principles.
- Swapping the LLM provider, vector store, or PDF parser is an adapter change, not a core
  change — matching the expectation that the stack and weights will evolve.
- Eval-first fits naturally: the harness drives the same core the CLI does, so quality is
  measured on the real decision logic.
- Clear seams make the PII-scrub-before-LLM boundary easy to enforce and audit.

**Costs / trade-offs**
- More upfront structure (ports, adapters, wiring) than a flat pipeline — slight overhead for
  a small team on a POC. Mitigated by keeping ports minimal and adding them only when a real
  second implementation or test seam demands it.
- Indirection can obscure flow for newcomers; the L2 container doc and the explicit pipeline
  ordering exist to counter that.

## Follow-ups (future ADRs)

- **Scoring & weighting policy** — how skill claims, project/client feedback, beach
  trajectory, and adjacency are combined; how location's priority weight is configured. (TBD)
- **Supply-state expansion** — adding roll-offs and new joiners (with date buffers and
  unverified-skill handling) after the beach-only slice. (TBD)
- **LLM determinism controls** — where temperature/seeding/caching are pinned to keep
  hard-constraint-adjacent reasoning predictable. (TBD)
