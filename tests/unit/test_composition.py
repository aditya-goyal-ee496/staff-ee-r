"""Composition root: all-null wiring runs end-to-end; the PII path fails closed."""

from __future__ import annotations

from datetime import date

import pytest

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


def test_llm_path_without_real_pii_scrubber_fails_closed() -> None:
    with pytest.raises(StaffeerError):
        build_matcher(StaffeerConfig(llm_enabled=True))


def test_semantic_path_without_real_pii_scrubber_fails_closed() -> None:
    with pytest.raises(StaffeerError):
        build_matcher(StaffeerConfig(semantic_enabled=True))
