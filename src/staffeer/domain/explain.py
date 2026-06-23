"""Explanation assembly — turn deterministic results into surfaced factors (Track A, slice 03).

Every factor that moved a consultant's standing is stated with the source backing it, so an
unexplained match is impossible (Principle 1). `Explanation` is an open list of
`ExplanationFactor`s that later tracks (semantic, soft-LLM) extend without contention. Pure,
no I/O (`docs/rules/hexagonal-architecture.md`).
"""

from __future__ import annotations

from staffeer.domain.models import EligibilityResult, ExplanationFactor, SkillScore


def skill_factor(coverage: SkillScore) -> ExplanationFactor:
    """Explain skill coverage: how many required skills matched, substituted, or are missing."""
    return ExplanationFactor(
        source="skills", summary=_coverage_summary(coverage), detail=coverage.detail
    )


def constraint_factors(result: EligibilityResult) -> tuple[ExplanationFactor, ...]:
    """One factor per hard-constraint check, so every gate that was applied is surfaced."""
    return tuple(
        ExplanationFactor(source=check.name, summary=check.reason) for check in result.checks
    )


def _coverage_summary(coverage: SkillScore) -> str:
    """A one-line tally of exact, adjacent, and missing required skills."""
    required = len(coverage.matched) + len(coverage.adjacent) + len(coverage.missing)
    return (
        f"{len(coverage.matched)} exact, {len(coverage.adjacent)} adjacent, "
        f"{len(coverage.missing)} missing of {required} required skills"
    )
