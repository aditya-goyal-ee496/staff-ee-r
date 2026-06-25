"""Ranking — turn scored consultants into an ordered shortlist (Track A, slice 03).

A match score is a **sum of named `ScoreContribution`s**, never a monolithic formula: each track
appends a contributor (skills here; semantic and soft-LLM later) and `assemble_match` sums them,
so the blend stays valid as contributors are added (`docs/tasks/parallelization-guide.md`). Pure,
no I/O (`.claude/principles/hexagonal-architecture.md`).
"""

from __future__ import annotations

from collections.abc import Iterable

from staffeer.domain.models import (
    Consultant,
    Explanation,
    Match,
    ScoreContribution,
    SkillScore,
)
from staffeer.ports.reasoner import SoftAssessment


def skill_contribution(coverage: SkillScore, weight: float = 1.0) -> ScoreContribution:
    """The deterministic skill-coverage contributor to a consultant's match score."""
    return ScoreContribution(
        source="skills", value=coverage.value, weight=weight, detail=coverage.detail
    )


def soft_contribution(assessment: SoftAssessment, weight: float = 1.0) -> ScoreContribution:
    """The soft LLM assessment contributor to a consultant's match score."""
    return ScoreContribution(
        source="soft_llm", value=assessment.score, weight=weight, detail=assessment.summary
    )


def assemble_match(
    consultant: Consultant,
    contributions: Iterable[ScoreContribution],
    explanation: Explanation | None = None,
) -> Match:
    """A `Match` scored as the sum of its weighted contributions (the contribution-sum rule)."""
    scored = tuple(contributions)
    return Match(
        consultant=consultant,
        score=sum(contribution.weighted for contribution in scored),
        contributions=scored,
        explanation=explanation or Explanation(),
    )


def rank(matches: Iterable[Match]) -> tuple[Match, ...]:
    """Order matches best-first by score, breaking ties by consultant name then id (stable)."""
    return tuple(
        sorted(
            matches, key=lambda match: (-match.score, match.consultant.name, match.consultant.id)
        )
    )
