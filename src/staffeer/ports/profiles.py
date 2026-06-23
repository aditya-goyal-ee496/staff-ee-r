"""`ProfileParser` port — turns a consultant profile document into structured data.

The spec (`docs/tasks/00b-contracts.md`): `parse(path)` returns a `ParsedProfile`; a malformed
or unreadable document is mapped to `ProfileParseError`. An implementation never fabricates
skills it did not read — absence yields an empty profile, not invented content (Principle 5).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from staffeer.domain.models import ValueObject


class ParsedProfile(ValueObject):
    """Structured output of parsing one profile document."""

    consultant_id: str
    text: str = ""
    skills: tuple[str, ...] = ()
    source: str | None = None


@runtime_checkable
class ProfileParser(Protocol):
    """Parses a profile document at `path` into a `ParsedProfile`."""

    def parse(self, path: Path) -> ParsedProfile:
        """Parse the document, or raise `ProfileParseError` if it cannot be read."""
        ...
