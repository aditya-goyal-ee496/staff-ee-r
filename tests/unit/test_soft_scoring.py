"""Unit tests for soft_contribution (I06-06) and soft_factor (I06-07) helpers.

Six one-assertion AAA tests.  All build SoftAssessment directly — no network, no LLM,
no adapters. Both helpers are additive-only additions to ranking.py and explain.py.
"""

from __future__ import annotations

from staffeer.domain.explain import soft_factor
from staffeer.domain.ranking import soft_contribution
from staffeer.ports.reasoner import SoftAssessment


def _assessment(
    *,
    score: float = 0.75,
    confidence: float = 0.9,
    cited_sources: tuple[str, ...] = ("profile", "feedback"),
    summary: str = "Good fit for the role.",
    abstained: bool = False,
) -> SoftAssessment:
    return SoftAssessment(
        score=score,
        confidence=confidence,
        cited_sources=cited_sources,
        summary=summary,
        abstained=abstained,
    )


def _abstaining_assessment() -> SoftAssessment:
    return SoftAssessment(
        score=0.0,
        confidence=0.0,
        cited_sources=(),
        summary="",
        abstained=True,
    )


# ---------------------------------------------------------------------------
# soft_contribution tests
# ---------------------------------------------------------------------------


def test_soft_contribution_source_is_soft_llm() -> None:
    # Arrange
    assessment = _assessment()
    # Act
    contribution = soft_contribution(assessment)
    # Assert
    assert contribution.source == "soft_llm"


def test_soft_contribution_weighted_value_equals_score_times_weight() -> None:
    # Arrange
    assessment = _assessment(score=0.8)
    weight = 2.0
    # Act
    contribution = soft_contribution(assessment, weight=weight)
    # Assert
    assert contribution.weighted == 0.8 * 2.0


# ---------------------------------------------------------------------------
# soft_factor tests (non-abstaining)
# ---------------------------------------------------------------------------


def test_soft_factor_summary_matches_assessment_summary() -> None:
    # Arrange
    assessment = _assessment(summary="Strong fit — backend skills confirmed.")
    # Act
    factor = soft_factor(assessment)
    # Assert
    assert factor.summary == "Strong fit — backend skills confirmed."


def test_soft_factor_detail_joins_cited_sources_with_comma_space() -> None:
    # Arrange
    assessment = _assessment(cited_sources=("profile", "feedback"))
    # Act
    factor = soft_factor(assessment)
    # Assert
    assert factor.detail == "profile, feedback"


# ---------------------------------------------------------------------------
# soft_factor tests (non-abstaining, no sources)
# ---------------------------------------------------------------------------


def test_soft_factor_detail_signals_gap_when_cited_sources_empty() -> None:
    # Arrange
    assessment = _assessment(cited_sources=())
    # Act
    factor = soft_factor(assessment)
    # Assert
    assert "[gap:" in factor.detail


# ---------------------------------------------------------------------------
# soft_factor tests (abstaining)
# ---------------------------------------------------------------------------


def test_abstaining_soft_factor_summary_starts_with_llm_abstained() -> None:
    # Arrange
    assessment = _abstaining_assessment()
    # Act
    factor = soft_factor(assessment)
    # Assert
    assert factor.summary.startswith("LLM abstained")


def test_abstaining_soft_factor_detail_is_empty() -> None:
    # Arrange
    assessment = _abstaining_assessment()
    # Act
    factor = soft_factor(assessment)
    # Assert
    assert factor.detail == ""
