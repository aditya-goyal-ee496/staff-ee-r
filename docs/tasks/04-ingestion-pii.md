# Slice 04 — Profile + feedback ingestion with PII scrubbing

**Goal:** bring richer signal into the system — parse consultant profile PDFs and feedback
markdown — and establish the PII-scrubbing boundary that all LLM-bound text must pass through.

**Type:** Feature · **Priority:** P1 · **Depends on:** C1 ([`00b-contracts.md`](00b-contracts.md))

> **Parallelization.** This needs only the C1 models + ports, not beach matching (02). The Docling
> + markdown-feedback adapters are **Track B**; the Presidio scrubber is **Track C** — both open
> after C1 and merge behind null-object defaults. The PII scrubber becomes the *required* default
> on any LLM/semantic path (fail-closed in `build_matcher`); it is consumed by I3/I4.
> See [`parallelization-guide.md`](parallelization-guide.md).

## Acceptance criteria

- [ ] Profile PDFs parse into structured text/skills via Docling behind a `ProfileParser` port.
- [ ] Feedback markdown loads per consultant behind a `FeedbackStore` port (client vs internal EE
      feedback distinguished; beach trajectory captured where present).
- [ ] `PIIScrubber` (Presidio + spaCy) removes names/emails/PII; **all** profile/feedback text is
      scrubbed before it could reach an LLM. Verified by test.
- [ ] Scrubbing actions are logged (structured) without logging the PII itself.

## Tasks

- [ ] **Ports** — `ProfileParser.parse(path) -> ParsedProfile`; `FeedbackStore.for_consultant(id)
      -> Feedback`; `PIIScrubber.scrub(text) -> ScrubbedText` (`ports/`).
- [ ] **Docling adapter** (`adapters/docling_profiles.py`) — parse templated + free-form PDFs;
      extract skills/experience; map parse failures to domain errors (no silent drop).
- [ ] **Feedback adapter** (`adapters/markdown_feedback.py`) — load `project_feedback/*.md`,
      associate to consultants by name/file convention; tag source type (client/internal/beach).
- [ ] **PII adapter** (`adapters/presidio_pii.py`) — Presidio analyzer+anonymizer with spaCy model;
      configurable entity list; deterministic redaction tokens.
- [ ] **Wiring** — a thin ingestion service composing parser+feedback+scrubber; scrubbing is
      mandatory on the path toward the reasoner (enforced, not optional).
- [ ] **Tests** — adapter integration tests on sampled real files (skip if absent); a unit test
      asserting scrubbed output contains no name/email from a known fixture (**security negative case**).
- [ ] **Docs** — note the model download step for spaCy in `README`/`Makefile` (`make install` hook).

## Notes

- New joiners' skills are **unverified** — tag provenance so later scoring can weight accordingly.
- `.claude/principles/security.md`: never log PII; validate/normalize parsed input at the boundary.
