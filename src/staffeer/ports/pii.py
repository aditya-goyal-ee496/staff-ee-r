"""`PIIScrubber` port — removes sensitive data before any text reaches an LLM.

The spec (`docs/tasks/00b-contracts.md`): `scrub(text)` returns a `ScrubbedText` carrying the
cleaned text and the entity types removed; it never raises on arbitrary input (a scrubber
failure is mapped to `PIIScrubbingError` so text cannot leak unscrubbed — fail closed,
`.claude/principles/security.md`).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from staffeer.domain.models import ValueObject


class ScrubbedText(ValueObject):
    """Text with PII removed, plus the entity types that were redacted (for audit)."""

    text: str
    redactions: tuple[str, ...] = ()


@runtime_checkable
class PIIScrubber(Protocol):
    """Scrubs PII from free text before it is sent to an LLM or semantic index."""

    def scrub(self, text: str) -> ScrubbedText:
        """Return `text` with PII removed and the redacted entity types recorded."""
        ...
