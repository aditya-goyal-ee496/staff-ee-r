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

- [x] Profile PDFs parse into structured text/skills via Docling behind a `ProfileParser` port.
- [x] Feedback markdown loads per consultant behind a `FeedbackStore` port (client vs internal EE
      feedback distinguished; beach trajectory captured where present).
- [x] `PIIScrubber` (Presidio + spaCy) removes names/emails/PII; **all** profile/feedback text is
      scrubbed before it could reach an LLM. Verified by test.
- [x] Scrubbing actions are logged (structured) without logging the PII itself.

## Tasks

- [x] **Ports** — `ProfileParser.parse(path) -> ParsedProfile`; `FeedbackStore.for_consultant(id)
      -> Feedback`; `PIIScrubber.scrub(text) -> ScrubbedText` (`ports/`).
- [x] **Docling adapter** (`adapters/docling_profiles.py`) — parse templated + free-form PDFs;
      extract skills/experience; map parse failures to domain errors (no silent drop).
- [x] **Feedback adapter** (`adapters/markdown_feedback.py`) — load `project_feedback/*.md`,
      associate to consultants by name/file convention; tag source type (client/internal/beach).
- [x] **PII adapter** (`adapters/presidio_pii.py`) — Presidio analyzer+anonymizer with spaCy model;
      configurable entity list; deterministic redaction tokens.
- [x] **Wiring** — a thin ingestion service composing parser+feedback+scrubber; scrubbing is
      mandatory on the path toward the reasoner (enforced, not optional).
- [x] **Tests** — adapter integration tests on sampled real files (skip if absent); a unit test
      asserting scrubbed output contains no name/email from a known fixture (**security negative case**).
- [x] **Docs** — note the model download step for spaCy in `README`/`Makefile` (`make install` hook).

## Spec — ProfileParser, FeedbackStore, PIIScrubber (additive amendment to C1)

> The three ports and their null-object adapters were frozen in C1 (`00b-contracts.md`). This
> spec records the **additive-only amendments** slice 04 makes so that the contract tests and
> real adapters stay in sync. No existing field or method is removed or renamed.

**Contract**

```python
# ports/profiles.py — additive field on ParsedProfile
class ParsedProfile(ValueObject):
    consultant_id: str
    text: str = ""
    skills: tuple[str, ...] = ()
    source: str | None = None
    skills_verified: bool = True          # NEW: False for new-joiner profiles

class ProfileParser(Protocol):
    def parse(self, path: Path) -> ParsedProfile: ...   # unchanged


# ports/feedback.py — additive field on Feedback
class Feedback(ValueObject):
    consultant_id: str
    client_notes: tuple[str, ...] = ()
    internal_notes: tuple[str, ...] = ()
    beach_notes: tuple[str, ...] = ()     # NEW: beach trajectory notes

class FeedbackStore(Protocol):
    def for_consultant(self, consultant_id: str) -> Feedback: ...   # unchanged


# ports/pii.py — unchanged
class ScrubbedText(ValueObject):
    text: str
    redactions: tuple[str, ...] = ()

class PIIScrubber(Protocol):
    def scrub(self, text: str) -> ScrubbedText: ...
```

**Invariants**

- `ParsedProfile.skills` is derived exclusively from the parsed document — no skills are
  fabricated when the document is absent or unreadable (Principle 5).
- `ParsedProfile.skills_verified` is `False` whenever the profile source is a new-joiner
  document; `True` otherwise (ensures downstream scoring can weight provenance).
- `Feedback.for_consultant` never returns `None`; a consultant with no markdown file yields
  an empty `Feedback` with all note tuples empty — never fabricated notes.
- Every `Feedback` separates client notes, internal EE notes, and beach trajectory notes so
  that callers can weight each source independently.
- `PIIScrubber.scrub` never raises on arbitrary input — infrastructure failures map to
  `PIIScrubbingError` so text cannot leak unscrubbed (fail-closed).
- All profile text and feedback text **must** pass through `PIIScrubber` before reaching any
  LLM or semantic index (`build_matcher` enforces this; `NullPIIScrubber` is not wired on the
  LLM/semantic path in production).
- Scrubbing actions are logged at `INFO` level (structured, entity types only) — the original
  PII text is never written to any log.

**Acceptance criteria**

- [x] `ParsedProfile` carries a `skills_verified` field defaulting to `True`; the Docling
      adapter sets it to `False` when parsing a new-joiner profile.
- [x] `Feedback` carries a `beach_notes` field; the markdown feedback adapter populates it
      from a `## Beach trajectory` section (or equivalent convention) when present.
- [x] The Presidio adapter's `scrub` removes at minimum `PERSON` and `EMAIL_ADDRESS` entities
      from a fixture containing a known name and email; the scrubbed output contains neither.
- [x] A security negative-case unit test: given a fixture with a known name/email, the
      scrubbed text does not contain the original name or email string.
- [x] `ProfileParseError` is raised (not swallowed) when Docling cannot read a PDF; the
      error message names the file path.
- [x] `FeedbackError` is raised (not swallowed) when a feedback file is malformed (e.g.
      unparseable markdown structure); absence of the file yields an empty `Feedback`, not an
      error.
- [x] Scrubbing actions are observable in structured logs (entity type emitted, raw PII not
      present in any log line) — verified by inspecting log output in the integration test.

**Error mapping**

- Docling cannot open / parse a PDF → `ProfileParseError` (file path in message)
- Markdown feedback file is malformed / unreadable → `FeedbackError`
- Presidio engine or spaCy model unavailable → `PIIScrubbingError`
- Any infrastructure exception in an adapter → mapped to the above at the boundary; never
  propagated as a raw `OSError`, `ValueError`, etc.

**Contract test:** `tests/contract/test_profiles.py`, `tests/contract/test_feedback.py`,
`tests/contract/test_pii.py` — extend each suite with the new assertions above. The null-object
adapters and every real adapter (Docling, markdown, Presidio) must pass the full suite.

---

## Notes

- New joiners' skills are **unverified** — tag provenance so later scoring can weight accordingly.
- `.claude/principles/security.md`: never log PII; validate/normalize parsed input at the boundary.
