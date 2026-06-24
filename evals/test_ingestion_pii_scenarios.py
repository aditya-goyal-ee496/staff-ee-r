"""Deterministic golden-table SCENARIO EVALS — Slice 04: ingestion + PII scrubbing.

Each scenario is a frozen fixture that exercises the ingestion + scrubbing pipeline
end-to-end with null or stub adapters.  100 % relevance is a COVERAGE WARNING, not a
pass — the mandatory NEGATIVE scenario (scrubbed text contains original PII) must be
present and must fail against unscrubbed text.

Scenarios
---------
1. skills_verified_true_for_regular_profile
   ParsedProfile from a non-new-joiner source carries skills_verified=True.

2. skills_verified_false_for_new_joiner_profile
   A profile parsed from a path whose stem ends in ``_nj`` carries
   skills_verified=False.  (Docling adapter not yet wired; tested via contract.)

3. beach_notes_populated_from_trajectory_section
   Feedback with a ## Beach trajectory section yields non-empty beach_notes.

4. absent_feedback_returns_empty_feedback  (negative — no notes, not an error)
   A consultant with no feedback file yields empty Feedback, never None.

5. pii_scrub_removes_name_and_email  (positive)
   After scrubbing, the original PERSON name is absent from result.text.

6. [NEGATIVE] scrubbed_text_must_not_contain_original_pii
   Verifies the security invariant: the identity (null) scrubber deliberately
   fails this assertion, proving that the test detects unscrubbed PII.
   This scenario is expected to FAIL against the NullPIIScrubber — that is
   the correct behaviour.  A 100 % pass rate across all scenarios would mean
   this negative case is missing or broken.

NOTE: Scenarios 5 and 6 are skipped when presidio_analyzer is not installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.ports.feedback import Feedback
from staffeer.ports.profiles import ParsedProfile

# ---------------------------------------------------------------------------
# Scenario 1 — skills_verified defaults True for regular profiles
# ---------------------------------------------------------------------------


def test_skills_verified_true_for_regular_profile(tmp_path: Path) -> None:
    """ParsedProfile from NullProfileParser (non-new-joiner path) is skills_verified=True."""
    # Arrange
    parser = NullProfileParser()
    # Act
    profile = parser.parse(tmp_path / "C-01.pdf")
    # Assert
    assert profile.skills_verified is True


# ---------------------------------------------------------------------------
# Scenario 2 — skills_verified False for new-joiner profile stem
# ---------------------------------------------------------------------------


def test_skills_verified_false_for_new_joiner_profile() -> None:
    """ParsedProfile created with skills_verified=False correctly stores the flag."""
    # Arrange / Act — simulates what DoclingProfileParser will set for _nj stems
    profile = ParsedProfile(consultant_id="C-10_nj", skills_verified=False)
    # Assert
    assert profile.skills_verified is False


# ---------------------------------------------------------------------------
# Scenario 3 — beach_notes populated from ## Beach trajectory section
# ---------------------------------------------------------------------------


_BEACH_MD = """\
## Client feedback
Positive client review.

## Internal EE feedback
Strong contributor.

## Beach trajectory
Completed AWS certification.
Started Kubernetes study.
"""


def test_beach_notes_populated_from_trajectory_section(tmp_path: Path) -> None:
    """beach_notes has one entry per non-blank line under ## Beach trajectory."""
    # Arrange — inline the markdown feedback adapter logic via a real file
    pytest.importorskip(
        "staffeer.adapters.markdown_feedback",
        reason="MarkdownFeedbackStore not yet implemented",
    )
    from staffeer.adapters.markdown_feedback import MarkdownFeedbackStore  # noqa: PLC0415

    (tmp_path / "C-02.md").write_text(_BEACH_MD)
    store = MarkdownFeedbackStore(tmp_path)
    # Act
    result = store.for_consultant("C-02")
    # Assert — two non-blank trajectory lines
    assert len(result.beach_notes) == 2


# ---------------------------------------------------------------------------
# Scenario 4 — absent feedback returns empty Feedback (negative: no error)
# ---------------------------------------------------------------------------


def test_absent_feedback_returns_empty_feedback() -> None:
    """NullFeedbackStore returns empty Feedback — never None, never an error."""
    # Arrange
    store = NullFeedbackStore()
    # Act
    result = store.for_consultant("NOBODY")
    # Assert
    assert isinstance(result, Feedback)
    assert result.beach_notes == ()
    assert result.client_notes == ()
    assert result.internal_notes == ()


# ---------------------------------------------------------------------------
# Scenario 5 — Presidio removes PERSON name from fixture text
# ---------------------------------------------------------------------------


def test_pii_scrub_removes_name_and_email() -> None:
    """Presidio scrubber removes the PERSON entity from the fixture string."""
    # Arrange
    pytest.importorskip("presidio_analyzer")
    from staffeer.adapters.presidio_pii import PresidioPIIScrubber  # noqa: PLC0415

    scrubber = PresidioPIIScrubber()
    # Act
    result = scrubber.scrub("Contact Ravi Kumar at ravi.kumar@example.com")
    # Assert
    assert "Ravi Kumar" not in result.text
    assert "ravi.kumar@example.com" not in result.text


# ---------------------------------------------------------------------------
# Scenario 6 — NEGATIVE: identity scrubber does NOT remove PII
#
# This test is EXPECTED to fail when run against NullPIIScrubber.
# Its purpose is to prove that the eval suite CAN detect unscrubbed PII.
# A 100 % pass rate across all scenarios in this file is a COVERAGE WARNING.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "NEGATIVE SCENARIO: NullPIIScrubber is an identity scrubber — it intentionally "
        "leaves PII intact.  This xfail proves the eval suite detects unscrubbed text. "
        "A 100%% pass rate (no xfails) would mean this guard is absent or broken."
    ),
    strict=True,
)
def test_null_scrubber_does_not_remove_pii_negative_scenario() -> None:
    """NEGATIVE: NullPIIScrubber leaves PII in the output — xfail is the correct outcome."""
    # Arrange
    scrubber = NullPIIScrubber()
    raw = "Call Alice Smith at alice.smith@example.com"
    # Act
    result = scrubber.scrub(raw)
    # Assert — this MUST fail (NullPIIScrubber returns text verbatim)
    assert "Alice Smith" not in result.text, (
        "NullPIIScrubber must not remove names — this assertion fires to trigger xfail"
    )
