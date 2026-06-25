# Slice 05b — Profile-text semantic embeddings

**Goal:** make semantic retrieval analyse the **consultant profile PDFs**, not just the one-line
xlsx summary. Today `staffeer index` embeds only `"{name} — {grade}, {location}. Skills: {skills}"`
built from `demand-supply.xlsx`; the 50 PDFs under `planning/raw-data/profiles/` are parsed by a
Docling adapter that is wired into nothing. This slice feeds PII-scrubbed profile text into the
semantic index so a role's intent can surface non-obvious fits from what a consultant actually did.

**Type:** Feature (integration, extends I3) · **Priority:** P1 · **Depends on:** I3 (semantic wiring, merged) + Track B (Docling `ProfileParser`, merged)

> **Context.** `ProfileParser.parse(path) -> ParsedProfile` (with `.text`, `.skills`,
> `.skills_verified`) already exists (Docling adapter, slice 04) but is never called in the index
> or match pipeline. `MilvusSemanticIndex` + the `--semantic` blend already work over the thin
> summary. This slice only changes **what text gets embedded** at index-build time — no port or
> scoring-contract change.

## Acceptance criteria

- [x] `staffeer index` embeds each consultant's **PII-scrubbed profile text** (from their PDF)
      combined with the existing structured summary, when a matching profile is found.
- [x] Profiles map to consultants by **normalised filename ↔ consultant `name`**: lowercase, strip
      a trailing `_pp`/`_nj` suffix, treat `_`/spaces as separators (e.g. `karan_mehta_pp.pdf` ↔
      `"Karan Mehta"`). The mapping is a **pure, unit-tested** function.
- [x] A consultant with **no matching profile** falls back to the summary-only text — never a
      fabricated or another consultant's profile (Principle 5). Unmatched profile files are skipped.
- [x] The profiles directory is **configurable** (`STAFFEER_PROFILES_DIR`, default the bundled
      `planning/raw-data/profiles/` when present).
- [x] `main` stays green without the `parse`/docling extra installed: index wiring is integration-
      tested with a **stub `ProfileParser`** (no real Docling in CI); real Docling runs are manual /
      heavy-lane only.

## Tasks

- [x] **Config** (`config.py`) — add `profiles_dir: str | None = None`; in `from_env` populate from
      `STAFFEER_PROFILES_DIR`, else the bundled profiles path if it exists. No other change.
- [x] **Domain mapping** (`domain/profile_match.py`, pure, no I/O) — `profile_key(value: str) -> str`
      (normalise a filename stem or a consultant name to a comparison key) and
      `resolve_profile_stem(name: str, stems: tuple[str, ...]) -> str | None` (return the stem whose
      key equals the name's key, else `None`). Unit-tested; functions < 20 lines.
- [x] **Index wiring** (`cli/main.py`) — in `index`, when `profiles_dir` resolves to an existing
      directory, build the matcher with `profiles_enabled=True`, list the `*.pdf` stems once, and for
      each consultant resolve their stem; if found, `matcher.profiles.parse(path)`, then compose the
      `IndexItem.text` as `summary + "\n\n" + parsed.text`; scrub the **combined** text via
      `matcher.pii.scrub(...)` before upsert; if not found, embed the summary alone. Print whether a
      profile was attached per consultant. Keep the command body < 20 lines (extract helpers); map a
      `ProfileParseError` to a skipped-profile warning (fall back to summary), never abort the build.
- [x] **Tests** — unit for `profile_key`/`resolve_profile_stem` (incl. `_pp` strip, no-match → None,
      and a case-insensitive match); integration for `index` with a **stub `ProfileParser`** and a
      `tmp_path` profiles dir containing one matching and one non-matching file — assert the matched
      consultant's `IndexItem.text` contains the profile text and the unmatched one falls back to the
      summary (the mandatory **negative / no-profile** case).
- [x] **Setup/docs** — add the `parse` extra to `setup.sh` (venv sync + `uv tool install`) and
      `make install`, and document `STAFFEER_PROFILES_DIR` in `.env.example`, so `staffeer index`
      can actually parse PDFs end-to-end. Note Docling is heavy (first run downloads models).

## Notes

- PII scrubbing of the **combined** text is mandatory before embedding (security; PDFs contain
  names/clients). Scrub once on the concatenated string.
- No fabrication: a missing/garbled profile yields summary-only embedding, surfaced in the index
  output, not invented content.
- Mapping is best-effort by name for now (per direction); a deterministic `consultant.id`↔file map
  can replace it later without touching the embedding logic.
