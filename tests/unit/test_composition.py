"""Composition root: all-null wiring runs end-to-end; the PII path fails closed."""

from __future__ import annotations

from datetime import date

import pytest

from staffeer.adapters.docling_profiles import DoclingProfileParser
from staffeer.adapters.markdown_feedback import MarkdownFeedbackStore
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.adapters.presidio_pii import PresidioPIIScrubber
from staffeer.composition import build_matcher
from staffeer.config import StaffeerConfig
from staffeer.domain.errors import StaffeerError
from staffeer.domain.models import Priority, Role


def _role() -> Role:
    return Role(
        id="ROLE-01",
        title="Backend Engineer",
        location="Chennai",
        start_date=date(2026, 7, 1),
        priority=Priority.HIGH,
    )


def test_all_null_matcher_returns_an_empty_shortlist() -> None:
    matcher = build_matcher(StaffeerConfig())
    assert matcher.match(_role()).matches == ()


def test_all_null_matcher_runs_without_error() -> None:
    shortlist = build_matcher(StaffeerConfig()).match(_role())
    assert shortlist.role.id == "ROLE-01"


def test_llm_path_wires_real_pii_scrubber() -> None:
    pytest.importorskip("presidio_analyzer")
    matcher = build_matcher(StaffeerConfig(llm_enabled=True))
    assert isinstance(matcher.pii, PresidioPIIScrubber)


def test_semantic_path_wires_real_pii_scrubber() -> None:
    pytest.importorskip("presidio_analyzer")
    matcher = build_matcher(StaffeerConfig(semantic_enabled=True))
    assert isinstance(matcher.pii, PresidioPIIScrubber)


def test_llm_path_with_null_scrubber_still_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "staffeer.composition._build_pii_scrubber", lambda config: NullPIIScrubber()
    )
    with pytest.raises(StaffeerError):
        build_matcher(StaffeerConfig(llm_enabled=True))


def test_profiles_enabled_wires_docling_profile_parser() -> None:
    matcher = build_matcher(StaffeerConfig(profiles_enabled=True))
    assert isinstance(matcher.profiles, DoclingProfileParser)


def test_feedback_dir_wires_markdown_feedback_store(tmp_path: pytest.TempPathFactory) -> None:
    matcher = build_matcher(StaffeerConfig(feedback_dir=str(tmp_path)))
    assert isinstance(matcher.feedback, MarkdownFeedbackStore)


def test_llm_enabled_without_key_falls_back_to_null_reasoner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_enabled=True with no api key must yield NullLLMReasoner, not raise."""
    pytest.importorskip("presidio_analyzer")
    matcher = build_matcher(StaffeerConfig(llm_enabled=True, openrouter_api_key=None))
    assert isinstance(matcher.reasoner, NullLLMReasoner)


def test_semantic_enabled_with_milvus_path_wires_milvus_semantic_index(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """semantic_enabled=True + milvus_path set must wire MilvusSemanticIndex."""
    pytest.importorskip("pymilvus")
    pytest.importorskip("presidio_analyzer")
    from staffeer.adapters.milvus_index import MilvusSemanticIndex

    monkeypatch.setattr(
        "staffeer.composition._build_pii_scrubber", lambda config: PresidioPIIScrubber()
    )
    matcher = build_matcher(StaffeerConfig(semantic_enabled=True, milvus_path=str(tmp_path)))
    assert isinstance(matcher.semantic_index, MilvusSemanticIndex)


def test_semantic_enabled_without_milvus_path_falls_back_to_null_index_and_warns(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """semantic_enabled=True with no milvus_path must yield NullSemanticIndex and log a warning."""
    pytest.importorskip("presidio_analyzer")
    import logging

    monkeypatch.setattr(
        "staffeer.composition._build_pii_scrubber", lambda config: PresidioPIIScrubber()
    )
    with caplog.at_level(logging.WARNING, logger="staffeer.composition"):
        matcher = build_matcher(StaffeerConfig(semantic_enabled=True, milvus_path=None))
    assert isinstance(matcher.semantic_index, NullSemanticIndex)
    assert any(
        "semantic_enabled_but_no_milvus_path_fallback_to_null" in r.message for r in caplog.records
    )
