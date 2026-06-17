# Slice 05 — Semantic retrieval (Milvus Lite)

**Goal:** complement lexical skill matching with semantic similarity so a role's intent (not
just exact tokens) retrieves relevant consultants.

**Type:** Feature · **Priority:** P1 · **Depends on:** 03, 04

## Acceptance criteria

- [ ] Consultant skills/profiles are embedded and stored in Milvus Lite behind a `SemanticIndex` port.
- [ ] A role query retrieves top-N semantically similar consultants with similarity scores.
- [ ] Semantic signal is blended into the score from slice 03 via a configurable weight.
- [ ] Index build is reproducible and idempotent; documented `make` target to (re)build it.

## Tasks

- [ ] **Port** — `SemanticIndex.upsert(items)`, `SemanticIndex.query(text, k) -> [Hit]` (`ports/`).
- [ ] **Embeddings** — choose an embedding model (local or OpenRouter); wrap behind the adapter so
      it is swappable. Document the choice in an ADR.
- [ ] **Milvus adapter** (`adapters/milvus_index.py`) — Milvus Lite collection for consultant
      vectors + metadata (id, skills); build + query; map errors to domain errors.
- [ ] **Blend** — extend `scoring.py` to combine lexical (03) + semantic similarity with a weight
      in the config object; keep the blend explainable (show both contributions).
- [ ] **CLI / Make** — `make index` to (re)build embeddings; `match` uses the index when present.
- [ ] **Tests** — adapter round-trip (upsert→query) on a small fixture; a test that a semantically
      related but lexically different skill is retrieved; a **no-relevant-match** negative case.

## Notes

- Embedding text must be PII-scrubbed (slice 04) before indexing.
- Keep semantic scoring a *complement*, not a replacement, for hard constraints (still deterministic).
