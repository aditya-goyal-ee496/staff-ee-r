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
    """Structured output of parsing one profile document (Slice 04: skills verification).

    Fields:
        consultant_id: Unique identifier for the consultant.
        text: Raw extracted text from the profile document.
        skills: Tuple of skills explicitly mentioned in the document (never fabricated).
        source: Profile source (beach, roll-off, new-joiner, etc.). None if unavailable.
        skills_verified: Whether skills were extracted from a verified source document
            (True for beach/roll-off; False for new-joiner profiles with unverified claims).
    """

    consultant_id: str
    text: str = ""
    skills: tuple[str, ...] = ()
    source: str | None = None
    skills_verified: bool = True


@runtime_checkable
class ProfileParser(Protocol):
    """Parses a profile document at `path` into a `ParsedProfile`."""

    def parse(self, path: Path) -> ParsedProfile:
        """Parse the document, or raise `ProfileParseError` if it cannot be read."""
        ...
