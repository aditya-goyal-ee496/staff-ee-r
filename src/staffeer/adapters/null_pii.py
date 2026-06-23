"""Null-object `PIIScrubber` — identity scrubber that redacts nothing.

Safe *only* because `build_matcher` fails closed: it raises if an LLM or semantic path is
wired with this null scrubber, so unscrubbed text can never reach an LLM
(`docs/tasks/00b-contracts.md`, `docs/rules/security.md`).
"""

from __future__ import annotations

from staffeer.ports.pii import ScrubbedText


class NullPIIScrubber:
    """Returns text unchanged with no redactions; never reaches an LLM (fail closed)."""

    def scrub(self, text: str) -> ScrubbedText:
        """Return `text` verbatim with an empty redaction list."""
        return ScrubbedText(text=text)
