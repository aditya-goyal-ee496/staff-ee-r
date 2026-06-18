"""Explanation behaviour: skill coverage and hard constraints are surfaced as factors."""

from __future__ import annotations

from staffeer.domain.explain import constraint_factors, skill_factor
from staffeer.domain.models import (
    ConstraintCheck,
    Consultant,
    EligibilityResult,
    SkillScore,
)


def test_skill_factor_summarises_the_coverage_tally() -> None:
    factor = skill_factor(SkillScore(value=0.5, matched=("python",), missing=("go",)))
    assert factor.summary == "1 exact, 0 adjacent, 1 missing of 2 required skills"


def test_skill_factor_carries_the_coverage_detail_for_audit() -> None:
    factor = skill_factor(SkillScore(value=1.0, matched=("python",), detail="matched python"))
    assert factor.detail == "matched python"


def test_constraint_factors_surface_each_check_with_its_reason() -> None:
    result = EligibilityResult(
        consultant=Consultant(id="C-01", name="Asha", location="Pune"),
        checks=(ConstraintCheck(name="location", passed=False, reason="Pune is not Chennai"),),
    )
    assert constraint_factors(result)[0].summary == "Pune is not Chennai"
