"""Domain model invariants: value objects are frozen and aggregate logic is correct."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from staffeer.domain.models import (
    ConstraintCheck,
    Consultant,
    EligibilityResult,
    Explanation,
    ExplanationFactor,
    ScoreContribution,
)


def test_consultant_is_immutable() -> None:
    consultant = Consultant(id="C-01", name="Asha Rao", location="Chennai")
    with pytest.raises(ValidationError):
        consultant.name = "Someone Else"


def test_eligibility_with_only_passing_checks_is_eligible() -> None:
    result = EligibilityResult(
        consultant=Consultant(id="C-01", name="Asha", location="Chennai"),
        checks=(ConstraintCheck(name="location", passed=True, reason="same city"),),
    )
    assert result.eligible is True


def test_eligibility_with_a_failing_check_is_not_eligible() -> None:
    result = EligibilityResult(
        consultant=Consultant(id="C-01", name="Asha", location="Pune"),
        checks=(ConstraintCheck(name="location", passed=False, reason="different city"),),
    )
    assert result.eligible is False


def test_failures_surfaces_only_the_failing_checks() -> None:
    result = EligibilityResult(
        consultant=Consultant(id="C-01", name="Asha", location="Pune"),
        checks=(
            ConstraintCheck(name="location", passed=False, reason="different city"),
            ConstraintCheck(name="start_date", passed=True, reason="available now"),
        ),
    )
    assert result.failures == (
        ConstraintCheck(name="location", passed=False, reason="different city"),
    )


def test_score_contribution_weights_its_value() -> None:
    contribution = ScoreContribution(source="skills", value=0.5, weight=2.0)
    assert contribution.weighted == 1.0


def test_with_factor_returns_an_explanation_carrying_the_new_factor() -> None:
    enriched = Explanation().with_factor(
        ExplanationFactor(source="skills", summary="all skills matched")
    )
    assert len(enriched.factors) == 1


def test_with_factor_leaves_the_original_explanation_unchanged() -> None:
    base = Explanation()
    base.with_factor(ExplanationFactor(source="skills", summary="all skills matched"))
    assert base.factors == ()
