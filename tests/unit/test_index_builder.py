"""Unit tests for the `IndexBuilder` application service (structure-only refactor of the index).

Uses stub ports — a stub ProfileParser returning a sentinel `ParsedProfile`, the `NullPIIScrubber`
adapter, and an in-memory fake SemanticIndex that collects upserts — so neither Docling nor Milvus
is required. One assertion per test; AAA layout.

Scenarios
---------
1. matched consultant -> IndexItem.text contains the profile sentinel; profile_attached True.
2. no matching stem (NEGATIVE) -> summary-only text lacks the sentinel; profile_attached False.
3. ProfileParseError -> summary-only fallback; profile_attached False.
"""

from __future__ import annotations

from pathlib import Path

from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.domain.errors import ProfileParseError
from staffeer.domain.index_builder import IndexBuilder
from staffeer.domain.models import Consultant, SupplyState
from staffeer.ports.profiles import ParsedProfile
from staffeer.ports.semantic_index import Hit, IndexItem

_PROFILE_CONTENT = "PROFILE_CONTENT"

_KARAN = Consultant(
    id="C-karan",
    name="Karan Mehta",
    location="Remote-India",
    state=SupplyState.BEACH,
)


class _StubProfileParser:
    """Returns a ParsedProfile with sentinel text; satisfies the ProfileParser port."""

    def parse(self, path: Path) -> ParsedProfile:
        return ParsedProfile(consultant_id=path.stem, text=_PROFILE_CONTENT)


class _RaisingProfileParser:
    """Always raises ProfileParseError to exercise the summary-only fallback."""

    def parse(self, path: Path) -> ParsedProfile:
        raise ProfileParseError("unreadable")


class _FakeSemanticIndex:
    """Collects every upserted IndexItem; query always returns empty."""

    def __init__(self) -> None:
        self.items: list[IndexItem] = []

    def upsert(self, item: IndexItem) -> None:
        self.items.append(item)

    def query(self, text: str, namespace: str, top_k: int) -> list[Hit]:
        return []


def _build_builder(parser: object, index: _FakeSemanticIndex) -> IndexBuilder:
    return IndexBuilder(profiles=parser, pii=NullPIIScrubber(), index=index)  # type: ignore[arg-type]


def test_matched_consultant_index_item_contains_profile_text() -> None:
    """When a stem matches, the upserted IndexItem text carries the parsed profile content."""
    # Arrange
    index = _FakeSemanticIndex()
    builder = _build_builder(_StubProfileParser(), index)
    # Act
    builder.build([_KARAN], Path("/profiles"), ("karan_mehta_pp",))
    # Assert
    assert _PROFILE_CONTENT in index.items[0].text


def test_unmatched_consultant_falls_back_to_summary_only() -> None:
    """NEGATIVE: with no matching stem, the IndexItem text must not contain the profile sentinel."""
    # Arrange
    index = _FakeSemanticIndex()
    builder = _build_builder(_StubProfileParser(), index)
    # Act
    builder.build([_KARAN], Path("/profiles"), ())
    # Assert
    assert _PROFILE_CONTENT not in index.items[0].text


def test_unmatched_consultant_outcome_reports_not_attached() -> None:
    """With no matching stem, the outcome reports profile_attached False."""
    # Arrange
    index = _FakeSemanticIndex()
    builder = _build_builder(_StubProfileParser(), index)
    # Act
    outcomes = builder.build([_KARAN], Path("/profiles"), ())
    # Assert
    assert outcomes[0].profile_attached is False


def test_matched_consultant_outcome_reports_attached() -> None:
    """When a stem matches, the outcome reports profile_attached True."""
    # Arrange
    index = _FakeSemanticIndex()
    builder = _build_builder(_StubProfileParser(), index)
    # Act
    outcomes = builder.build([_KARAN], Path("/profiles"), ("karan_mehta_pp",))
    # Assert
    assert outcomes[0].profile_attached is True


def test_parse_error_falls_back_to_summary_only() -> None:
    """When the parser raises ProfileParseError, the IndexItem text omits the profile sentinel."""
    # Arrange
    index = _FakeSemanticIndex()
    builder = _build_builder(_RaisingProfileParser(), index)
    # Act
    builder.build([_KARAN], Path("/profiles"), ("karan_mehta_pp",))
    # Assert
    assert _PROFILE_CONTENT not in index.items[0].text


def test_parse_error_outcome_reports_not_attached() -> None:
    """When the parser raises ProfileParseError, the outcome reports profile_attached False."""
    # Arrange
    index = _FakeSemanticIndex()
    builder = _build_builder(_RaisingProfileParser(), index)
    # Act
    outcomes = builder.build([_KARAN], Path("/profiles"), ("karan_mehta_pp",))
    # Assert
    assert outcomes[0].profile_attached is False
