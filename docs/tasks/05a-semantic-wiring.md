# Slice 05a — Semantic blend wiring (complete I3)

**Goal:** turn semantic retrieval *on* during matching. Slice 05 (Track D) built the
`MilvusSemanticIndex` adapter, the semantic `ScoreContribution`, and `make index`, but no
matching command ever enables it — `match` and `match-text` both wire `NullSemanticIndex`, so the
semantic contribution is always `0.0` end to end. This slice delivers the missing **I3** piece:
the `--semantic` enablement so the index that `make index` builds is actually queried, and the
semantic signal genuinely moves the rank.

**Type:** Feature (integration I3) · **Priority:** P1 · **Depends on:** slice 05 (`05-semantic-retrieval.md`)

> **Context (the gap).** `StaffeerConfig.from_env()` never sets `semantic_enabled`, so it stays
> `False`; `build_matcher` therefore wires `NullSemanticIndex` (query → `[]` → semantic value
> `0.0`) on every match path. The `index` command already forces `semantic_enabled=True` to build
> the index, but nothing reads from it at match time. The I3 row in
> [`parallelization-guide.md`](parallelization-guide.md) explicitly lists a `--semantic` flag as
> part of the wiring; it was not delivered in slice 05.

## Acceptance criteria

- [x] `match` and `match-text` query the semantic index when semantic retrieval is enabled, so a
      populated index yields a non-zero semantic contribution that can change the ranking.
- [x] Semantic retrieval is enabled via a `--semantic` CLI flag (thin override merged into
      `StaffeerConfig`, per the "CLI flags are thin overrides" rule), requiring `milvus_path` to be
      set; a clear error is shown when `--semantic` is passed without `STAFFEER_MILVUS_PATH`.
- [x] The blend weight stays configurable; the default per-contributor weights are made explicit
      (no behaviour change vs the implicit `1.0`) so the blend is intentional, not accidental.
- [x] An **end-to-end** test proves that a *built* (populated) semantic index changes the shortlist
      ordering relative to the null/empty index — the signal demonstrably moves the rank.
- [x] Fail-closed PII still holds (`--semantic` ⇒ real `PIIScrubber`); `main` stays green with the
      semantic extra absent (flag off by default; null wiring unchanged).

## Tasks

- [x] **CLI flag** (`cli/main.py`) — add `--semantic` to `match` and `match-text`. When set, merge
      `semantic_enabled=True` into the config before `build_matcher`; if `milvus_path` is unset,
      print an error and exit 1 (mirror the `index` command's guard). Keep the command bodies
      cohesive; extract a small helper if a body would exceed 20 lines.
- [x] **Weights default** (`config.py`) — seed an explicit default `weights` mapping
      (`skills`/`soft_llm`/`semantic`) equal to today's implicit `1.0` each, documented as the
      tunable blend (Principle 4). No ranking change for existing callers.
- [x] **End-to-end test** (`tests/integration/`) — with the `semantic`/`pymilvus` extras present
      (`importorskip`), build an index over a small fixture, run a match with semantic enabled, and
      assert the ranking differs from the same match with the null index (a lexically-weak but
      semantically-strong consultant ranks higher only when semantic is on). Include the
      semantic-off path as the negative/control case.
- [x] **Docs** — note the `--semantic` flag in the CLI usage (README and/or `make match` help) and
      cross-reference `make index`.

## Notes

- This is purely additive wiring against the frozen `SemanticIndex` port — no contract change, so
  the spec stage should self-skip.
- Embedding text is already PII-scrubbed in the matcher pipeline; enabling `--semantic` only flips
  which adapter is wired, it does not change the scrub boundary.
- Keep semantic a *complement* to the deterministic hard-constraint screen — `--semantic` must not
  relax location/start-date filtering.
