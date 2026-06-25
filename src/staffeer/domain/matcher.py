"""`Matcher` — the application service that runs the matching pipeline over the ports.

It depends only on port abstractions and pure domain functions (never on adapters or config), so
it stays testable. The pipeline for one role is **filter → score → rank → explain**: screen the
supply for hard-constraint eligibility, score each eligible consultant's skill coverage, rank by
the contribution-sum, and attach an explanation. Excluded consultants are carried through with
their reasons (no silent drops). Soft signals (semantic, LLM) append later behind this signature.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from staffeer.domain.eligibility import screen_consultants
from staffeer.domain.explain import constraint_factors, semantic_factor, skill_factor, soft_factor
from staffeer.domain.models import (
    Consultant,
    EligibilityResult,
    Explanation,
    Match,
    Role,
    ScoreContribution,
    Shortlist,
    SkillScore,
    SupplyState,
)
from staffeer.domain.ranking import (
    assemble_match,
    rank,
    semantic_contribution,
    skill_contribution,
    soft_contribution,
)
from staffeer.domain.scoring import skill_coverage
from staffeer.ports.feedback import FeedbackStore
from staffeer.ports.pii import PIIScrubber
from staffeer.ports.profiles import ProfileParser
from staffeer.ports.reasoner import LLMReasoner, SoftAssessment
from staffeer.ports.semantic_index import Hit, SemanticIndex
from staffeer.ports.supply_demand import SupplyDemandSource


@dataclass(frozen=True)
class Matcher:
    """Orchestrates filter -> score -> rank -> explain for one role."""

    supply: SupplyDemandSource
    profiles: ProfileParser
    feedback: FeedbackStore
    pii: PIIScrubber
    semantic_index: SemanticIndex
    reasoner: LLMReasoner
    include_states: tuple[SupplyState, ...] = (SupplyState.BEACH,)
    weights: Mapping[str, float] = field(default_factory=dict)

    def match(self, role: Role) -> Shortlist:
        """Return the ranked, explained shortlist for `role`, with explained exclusions."""
        screened = screen_consultants(self.supply.consultants(*self.include_states), role)
        matches = rank(self._match_for(result, role) for result in screened if result.eligible)
        excluded = tuple(result for result in screened if not result.eligible)
        return Shortlist(role=role, matches=matches, excluded=excluded)

    def _match_for(self, result: EligibilityResult, role: Role) -> Match:
        """Score and explain one eligible consultant against `role`."""
        coverage = skill_coverage(role, result.consultant)
        scrubbed_role, scrubbed_consultant = self._scrub_inputs(role, result.consultant)
        assessment = self._assess(scrubbed_consultant, scrubbed_role)
        all_hits = self._query_semantic(scrubbed_role)
        hits = [h for h in all_hits if h.id == result.consultant.id]
        return assemble_match(
            result.consultant,
            _build_contributions(coverage, assessment, hits, self.weights),
            _build_explanation(result, coverage, assessment, hits),
        )

    def _scrub_inputs(self, role: Role, consultant: Consultant) -> tuple[str, str]:
        """Build and PII-scrub the role description and consultant summary."""
        scrubbed_role = self.pii.scrub(_build_role_description(role)).text
        scrubbed_consultant = self.pii.scrub(_build_consultant_summary(consultant)).text
        return scrubbed_role, scrubbed_consultant

    def _assess(self, scrubbed_consultant: str, scrubbed_role: str) -> SoftAssessment:
        """Call the LLM reasoner; returns an abstaining assessment if the port fails."""
        try:
            return self.reasoner.assess(
                consultant_summary=scrubbed_consultant, role_description=scrubbed_role
            )
        except Exception:  # noqa: BLE001
            return SoftAssessment(score=0.0, confidence=0.0, abstained=True)

    def _query_semantic(self, scrubbed_role_text: str) -> list[Hit]:
        """Query the semantic index; returns empty list if the index is unavailable."""
        try:
            return self.semantic_index.query(scrubbed_role_text, namespace="skills", top_k=5)
        except Exception:  # noqa: BLE001
            return []


def _build_contributions(
    coverage: SkillScore,
    assessment: SoftAssessment,
    hits: list[Hit],
    weights: Mapping[str, float],
) -> tuple[ScoreContribution, ...]:
    """Assemble the three score contributions from their respective port results."""
    return (
        skill_contribution(coverage, weights.get("skills", 1.0)),
        soft_contribution(assessment, weights.get("soft_llm", 1.0)),
        semantic_contribution(hits, weights.get("semantic", 1.0)),
    )


def _build_explanation(
    result: EligibilityResult,
    coverage: SkillScore,
    assessment: SoftAssessment,
    hits: list[Hit],
) -> Explanation:
    """Assemble all explanation factors for one consultant match."""
    return Explanation(
        factors=(
            *constraint_factors(result),
            skill_factor(coverage),
            soft_factor(assessment),
            semantic_factor(hits),
        )
    )


def _build_consultant_summary(consultant: Consultant) -> str:
    """Build a plain-text summary of a consultant for LLM assessment."""
    skills = ", ".join(consultant.skills) if consultant.skills else "none"
    grade = consultant.grade or "consultant"
    return f"{consultant.name} — {grade}, {consultant.location}. Skills: {skills}."


def _build_role_description(role: Role) -> str:
    """Build a plain-text description of a role for LLM assessment."""
    required = ", ".join(role.required_skills) if role.required_skills else "none"
    return f"{role.title} in {role.location}. Required skills: {required}."
