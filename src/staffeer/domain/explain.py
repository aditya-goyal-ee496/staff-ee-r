"""Explanation assembly — turn deterministic results into surfaced factors (Track A, slice 03).

Every factor that moved a consultant's standing is stated with the source backing it, so an
unexplained match is impossible (Principle 1). `Explanation` is an open list of
`ExplanationFactor`s that later tracks (semantic, soft-LLM) extend without contention. Pure,
no I/O (`.claude/principles/hexagonal-architecture.md`).
"""

from __future__ import annotations

from staffeer.domain.models import EligibilityResult, ExplanationFactor, SkillScore
from staffeer.ports.reasoner import SoftAssessment
from staffeer.ports.semantic_index import Hit

SKILLS_SOURCE: str = "skills"
"""Canonical source label for the skill-coverage ExplanationFactor.

Use this constant wherever code compares or assigns ``ExplanationFactor.source`` for
skills — a rename here propagates at compile time rather than silently diverging.
"""

SOFT_LLM_SOURCE: str = "soft_llm"
"""Canonical source label for the soft-LLM assessment ExplanationFactor.

Use this constant wherever code compares or assigns ``ExplanationFactor.source`` for
soft-LLM assessments — a rename here propagates at compile time rather than silently diverging.
"""

SEMANTIC_SOURCE: str = "semantic"
"""Canonical source label for the semantic similarity ExplanationFactor.

Use this constant wherever code compares or assigns ``ExplanationFactor.source`` for
semantic matches — a rename here propagates at compile time rather than silently diverging.
"""


def skill_factor(coverage: SkillScore) -> ExplanationFactor:
    """Explain skill coverage: how many required skills matched, substituted, or are missing."""
    return ExplanationFactor(
        source=SKILLS_SOURCE, summary=_coverage_summary(coverage), detail=coverage.detail
    )


def constraint_factors(result: EligibilityResult) -> tuple[ExplanationFactor, ...]:
    """One factor per hard-constraint check, so every gate that was applied is surfaced."""
    return tuple(
        ExplanationFactor(source=check.name, summary=check.reason) for check in result.checks
    )


def soft_factor(assessment: SoftAssessment) -> ExplanationFactor:
    """Explain soft-LLM assessment: reasoning and confidence with cited sources."""
    if assessment.abstained:
        return ExplanationFactor(
            source=SOFT_LLM_SOURCE,
            summary="LLM abstained: insufficient evidence",
            detail="",
        )
    detail = (
        ", ".join(assessment.cited_sources)
        if assessment.cited_sources
        else "[gap: no sources cited]"
    )
    return ExplanationFactor(
        source=SOFT_LLM_SOURCE,
        summary=assessment.summary,
        detail=detail,
    )


def semantic_factor(hits: list[Hit]) -> ExplanationFactor:
    """Explain semantic similarity: whether semantic matches were found and the top score."""
    if not hits:
        return ExplanationFactor(
            source=SEMANTIC_SOURCE,
            summary="no semantic matches found",
            detail="",
        )
    detail = ", ".join(h.id for h in hits)
    return ExplanationFactor(
        source=SEMANTIC_SOURCE,
        summary=f"top semantic similarity {hits[0].score:.2f}",
        detail=detail,
    )


def _coverage_summary(coverage: SkillScore) -> str:
    """A one-line tally of matched, adjacent, and missing required skills."""
    required = len(coverage.matched) + len(coverage.adjacent) + len(coverage.missing)
    return (
        f"{len(coverage.matched)} matched, {len(coverage.adjacent)} adjacent, "
        f"{len(coverage.missing)} missing of {required} required skills"
    )
