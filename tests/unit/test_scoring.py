"""Skill-coverage behaviour: full/partial match, adjacency substitution, surfaced gaps.

Tests assert the observable score and the matched/adjacent/missing skills a reviewer sees,
not how coverage is computed (RULE-006).
"""

from __future__ import annotations

from staffeer.domain.models import Consultant, Role
from staffeer.domain.scoring import skill_coverage


def _consultant(*skills: str) -> Consultant:
    return Consultant(id="C-01", name="Asha Rao", location="Chennai", skills=skills)


def _role(*required: str) -> Role:
    return Role(id="R-01", title="Engineer", location="Chennai", required_skills=required)


def test_full_exact_coverage_scores_one() -> None:
    score = skill_coverage(_role("python", "kubernetes"), _consultant("Python", "k8s"))
    assert score.value == 1.0


def test_partial_coverage_scores_the_matched_fraction() -> None:
    score = skill_coverage(_role("python", "go"), _consultant("python"))
    assert score.value == 0.5


def test_adjacency_substitution_scores_below_an_exact_match() -> None:
    role = _role("kotlin")
    substitute = skill_coverage(role, _consultant("java")).value
    exact = skill_coverage(role, _consultant("kotlin")).value
    assert substitute < exact


def test_adjacency_substitution_is_surfaced_as_an_adjacent_skill() -> None:
    score = skill_coverage(_role("kotlin"), _consultant("java"))
    assert score.adjacent == ("kotlin",)


def test_uncovered_required_skill_is_surfaced_as_missing() -> None:
    score = skill_coverage(_role("python", "go"), _consultant("python"))
    assert score.missing == ("go",)


def test_coverage_detail_names_the_adjacency_substitution() -> None:
    score = skill_coverage(_role("kotlin"), _consultant("java"))
    assert "kotlin via java" in score.detail


def test_a_role_with_no_required_skills_is_fully_covered() -> None:
    score = skill_coverage(_role(), _consultant("python"))
    assert score.value == 1.0
