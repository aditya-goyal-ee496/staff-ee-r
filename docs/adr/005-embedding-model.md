# ADR-005: Embedding model for consultant profile embeddings

## Status: Accepted

## Context

Semantic similarity search over consultant profiles requires embedding text (already scrubbed of
PII) before Milvus Lite storage. We need: local execution (no API latency), deterministic output
(same text → same vector), lightweight install (optional dependency), and permissive license
(Parity Partners owns deployment).

Remote APIs (OpenAI, HuggingFace, Cohere) add latency, require keys, and introduce versioning
variance. Local models trade one-time download for determinism and ownership.

## Decision

Use **`sentence-transformers` with `all-MiniLM-L6-v2`** — a 33M-parameter, 384-dim bilingual
encoder (MIT license) cached to `~/.cache/huggingface/` after first download.

The `MilvusSemanticIndex` adapter loads the model once in `__init__`, encodes text on upsert/query,
and persists vectors. To swap models, pass a different `model_name` (e.g., `"all-mpnet-base-v2"`)
— the adapter architecture remains unchanged. Dependencies in `pyproject.toml` `semantic` extra:
`sentence-transformers>=3.0`, `pymilvus[milvus_lite]>=2.4`.

## Consequences

**Good**
- Deterministic vectors enable repeatable, unit-testable matching (no API versioning drift).
- Local generation preserves consultant data (no external transmission).
- Fast query execution; scales horizontally without API rate limits.
- Model swaps require only a config change; no architecture refactoring.

**Costs**
- ~1.2 GB install overhead (PyTorch + model weights); mitigated by optional `semantic` extra.
- General-purpose embeddings may miss consulting-domain nuances. If evals show inadequate ranking,
  domain-specific fine-tuning or `all-mpnet-base-v2` can substitute without code changes.

## Follow-ups

Domain-tuning if generic embeddings prove insufficient for role-consultant matching quality.
