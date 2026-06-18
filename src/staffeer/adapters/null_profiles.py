"""Null-object `ProfileParser` — satisfies the port while parsing nothing.

Used as the default wiring until the Docling adapter lands (Track B). It fabricates no
skills: an unwired parser yields an empty profile, never invented content (Principle 5).
"""

from __future__ import annotations

from pathlib import Path

from staffeer.ports.profiles import ParsedProfile


class NullProfileParser:
    """Returns an empty `ParsedProfile` for any path; does no I/O."""

    def parse(self, path: Path) -> ParsedProfile:
        """Return an empty profile keyed by the file stem, with no skills."""
        return ParsedProfile(consultant_id=path.stem, source="null")
