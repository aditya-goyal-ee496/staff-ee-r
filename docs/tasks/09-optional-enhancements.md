# Slice 09 — Optional enhancements

**Goal:** stretch goals beyond the core matcher. Only start after 06/07 are solid; each is
independently optional.

**Type:** Epic (optional) · **Priority:** P3 · **Depends on:** I4

> **Parallelization.** Each item is integration slice **I7** — a new driving adapter or use case
> over the **unchanged** domain core, so they are mutually parallel and fully optional. The
> hexagonal boundary keeps them additive (e.g. persistence is a new `SupplyDemandSource` adapter
> behind the existing port). See [`parallelization-guide.md`](parallelization-guide.md).

## Candidate work items (use /clarify + /breakdown before starting each)

- [ ] **Multi-role / team formation** — match a set of roles jointly, avoiding double-booking a
      consultant; surface team-level trade-offs. (New driving use case over the same core.)
- [ ] **Batch file input** — accept a file of open roles and emit shortlists for each.
- [ ] **Web interface** — a thin web driving adapter over the core. If built, follow
      `docs/rules/api-design.md` (versioned `/v1`, consistent errors, pagination) and
      `docs/rules/security.md` (authn/z, input validation, headers).
- [ ] **Persistence** — move supply/demand from xlsx to a database adapter behind the existing port.
- [ ] **Observability** — metrics/tracing for the pipeline and LLM calls.

## Notes

- Each enhancement is a new adapter or use case over the unchanged domain core — the hexagonal
  boundary should make these additive, not invasive.
- Re-evaluate priority with the business after the POC is validated (development philosophy).
