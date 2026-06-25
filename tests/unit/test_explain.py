"""Explanation behaviour: skill coverage and hard constraints are surfaced as factors."""

from __future__ import annotations

from staffeer.domain.explain import constraint_factors, semantic_factor, skill_factor
from staffeer.domain.models import (
    ConstraintCheck,
    Consultant,
    EligibilityResult,
    SkillScore,
)
from staffeer.ports.semantic_index import Hit


def test_skill_factor_summarises_the_coverage_tally() -> None:
    factor = skill_factor(SkillScore(value=0.5, matched=("python",), missing=("go",)))
    assert factor.summary == "1 matched, 0 adjacent, 1 missing of 2 required skills"


def test_skill_factor_carries_the_coverage_detail_for_audit() -> None:
    factor = skill_factor(SkillScore(value=1.0, matched=("python",), detail="matched python"))
    assert factor.detail == "matched python"


def test_constraint_factors_surface_each_check_with_its_reason() -> None:
    result = EligibilityResult(
        consultant=Consultant(id="C-01", name="Asha", location="Pune"),
        checks=(ConstraintCheck(name="location", passed=False, reason="Pune is not Chennai"),),
    )
    assert constraint_factors(result)[0].summary == "Pune is not Chennai"


# ---------------------------------------------------------------------------
# semantic_factor tests (05-13)
# ---------------------------------------------------------------------------


def test_semantic_factor_no_hits_reports_no_semantic_matches() -> None:
    """AAA: empty hits list -> summary says no semantic matches found."""
    # Arrange
    hits: list[Hit] = []
    # Act
    factor = semantic_factor(hits)
    # Assert
    assert "no semantic matches found" in factor.summary


def test_semantic_factor_with_hits_shows_top_score() -> None:
    """AAA: hits present -> summary includes the top similarity score."""
    # Arrange
    hits = [
        Hit(id="C-01", score=0.85, text="python django web development"),
        Hit(id="C-02", score=0.4, text="java backend"),
    ]
    # Act
    factor = semantic_factor(hits)
    # Assert
    assert "0.85" in factor.summary
