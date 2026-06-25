"""`IndexBuilder` — the application service that builds the semantic index from supply data.

Mirrors `Matcher`: it depends only on port abstractions and pure domain functions (never on
adapters, config, or the filesystem), so it stays testable. For each consultant it resolves a
profile stem, builds the index text (summary, optionally enriched with the parsed profile),
PII-scrubs it, and upserts an `IndexItem`. The directory glob that discovers profile stems stays
in the CLI driving adapter; this service only constructs paths (pure) and orchestrates the ports.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from staffeer.domain.errors import ProfileParseError
from staffeer.domain.matcher import _build_consultant_summary
from staffeer.domain.models import Consultant, ValueObject
from staffeer.domain.profile_match import resolve_profile_stem
from staffeer.ports.pii import PIIScrubber
from staffeer.ports.profiles import ProfileParser
from staffeer.ports.semantic_index import IndexItem, SemanticIndex


class IndexOutcome(ValueObject):
    """The result of indexing one consultant: whether profile text was attached."""

    consultant_id: str
    profile_attached: bool


@dataclass(frozen=True)
class IndexBuilder:
    """Orchestrates resolve -> build text -> scrub -> upsert for every consultant."""

    profiles: ProfileParser
    pii: PIIScrubber
    index: SemanticIndex

    def build(
        self,
        consultants: Iterable[Consultant],
        profiles_dir: Path | None,
        stems: tuple[str, ...],
    ) -> list[IndexOutcome]:
        """Index every consultant; return one `IndexOutcome` per consultant in order."""
        outcomes: list[IndexOutcome] = []
        for consultant in consultants:
            profile_path = _resolve_profile_path(consultant, profiles_dir, stems)
            text, attached = self._text_for(consultant, profile_path)
            self.index.upsert(_index_item(consultant, text))
            outcomes.append(IndexOutcome(consultant_id=consultant.id, profile_attached=attached))
        return outcomes

    def _text_for(self, consultant: Consultant, profile_path: Path | None) -> tuple[str, bool]:
        """Return (scrubbed_text, profile_attached); summary-only when no profile is available."""
        summary = _build_consultant_summary(consultant)
        if profile_path is None:
            return self.pii.scrub(summary).text, False
        try:
            parsed = self.profiles.parse(profile_path)
        except ProfileParseError:
            return self.pii.scrub(summary).text, False
        combined = summary + "\n\n" + parsed.text
        return self.pii.scrub(combined).text, True


def _resolve_profile_path(
    consultant: Consultant, profiles_dir: Path | None, stems: tuple[str, ...]
) -> Path | None:
    """Construct profiles_dir / f'{stem}.pdf' when a stem matches and a dir is given (pure)."""
    if profiles_dir is None:
        return None
    stem = resolve_profile_stem(consultant.name, stems)
    return profiles_dir / f"{stem}.pdf" if stem else None


def _index_item(consultant: Consultant, text: str) -> IndexItem:
    """Build the skills-namespace `IndexItem` for one consultant from scrubbed text."""
    return IndexItem(
        id=consultant.id,
        text=text,
        namespace="skills",
        metadata={"location": consultant.location, "state": str(consultant.state)},
    )
