"""Integration tests for slice 05b (I8) — index wiring attaches profile text.

Uses a stub ProfileParser and an in-memory fake SemanticIndex so neither
Docling nor Milvus is required.  Tests are marked `integration`.

Scenarios
---------
1. test_matched_consultant_index_item_contains_profile_text
   When a PDF exists for a consultant, the upserted IndexItem.text contains the
   parsed profile text (not just the xlsx summary).

2. test_unmatched_consultant_falls_back_to_summary (NEGATIVE)
   When no PDF exists for a consultant, the upserted IndexItem.text does NOT
   contain the profile parse sentinel — only the summary is embedded.

One assertion per test; AAA layout; no mocking of domain logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.cli.main import _index_all
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import Consultant, SupplyState
from staffeer.ports.profiles import ParsedProfile
from staffeer.ports.semantic_index import Hit, IndexItem

pytestmark = pytest.mark.integration

_PROFILE_CONTENT = "PROFILE_CONTENT"


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubProfileParser:
    """Returns a ParsedProfile with sentinel text; satisfies the ProfileParser port."""

    def parse(self, path: Path) -> ParsedProfile:
        return ParsedProfile(consultant_id=path.stem, text=_PROFILE_CONTENT)


class _FakeSemanticIndex:
    """Collects every upserted IndexItem in a list; query always returns empty."""

    def __init__(self) -> None:
        self.items: list[IndexItem] = []

    def upsert(self, item: IndexItem) -> None:
        self.items.append(item)

    def query(self, text: str, namespace: str, top_k: int) -> list[Hit]:
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_KARAN = Consultant(
    id="C-karan",
    name="Karan Mehta",
    location="Remote-India",
    state=SupplyState.BEACH,
)

_NOBODY = Consultant(
    id="C-nobody",
    name="Nobody Here",
    location="Remote-India",
    state=SupplyState.BEACH,
)


def _build_matcher(fake_index: _FakeSemanticIndex) -> Matcher:
    supply = InMemorySupplyDemandSource(consultants=(_KARAN, _NOBODY))
    return Matcher(
        supply=supply,
        profiles=_StubProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=fake_index,
        reasoner=NullLLMReasoner(),
        include_states=(SupplyState.BEACH,),
    )


def _profiles_dir_with_karan(tmp_path: Path) -> Path:
    """Create a tmp profiles dir containing only karan_mehta_pp.pdf."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "karan_mehta_pp.pdf").touch()
    return profiles_dir


# ---------------------------------------------------------------------------
# Test 1 — matched consultant's IndexItem contains profile text
# ---------------------------------------------------------------------------


def test_matched_consultant_index_item_contains_profile_text(tmp_path: Path) -> None:
    """When a matching PDF exists, the IndexItem for Karan contains the parsed profile text."""
    # Arrange
    profiles_dir = _profiles_dir_with_karan(tmp_path)
    fake_index = _FakeSemanticIndex()
    matcher = _build_matcher(fake_index)
    # Act
    _index_all(matcher, profiles_dir)
    karan_item = next(item for item in fake_index.items if item.id == _KARAN.id)
    # Assert
    assert _PROFILE_CONTENT in karan_item.text


# ---------------------------------------------------------------------------
# Test 2 (NEGATIVE) — unmatched consultant falls back to summary-only text
# ---------------------------------------------------------------------------


def test_unmatched_consultant_falls_back_to_summary(tmp_path: Path) -> None:
    """NEGATIVE: when no PDF matches 'Nobody Here', the IndexItem must NOT contain profile text."""
    # Arrange
    profiles_dir = _profiles_dir_with_karan(tmp_path)
    fake_index = _FakeSemanticIndex()
    matcher = _build_matcher(fake_index)
    # Act
    _index_all(matcher, profiles_dir)
    nobody_item = next(item for item in fake_index.items if item.id == _NOBODY.id)
    # Assert — summary-only fallback: profile sentinel must be absent
    assert _PROFILE_CONTENT not in nobody_item.text
