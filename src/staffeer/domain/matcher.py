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
from staffeer.domain.explain import constraint_factors, skill_factor
from staffeer.domain.models import (
    EligibilityResult,
    Explanation,
    Match,
    Role,
    Shortlist,
    SupplyState,
)
from staffeer.domain.ranking import assemble_match, rank, skill_contribution
from staffeer.domain.scoring import skill_coverage
from staffeer.ports.feedback import FeedbackStore
from staffeer.ports.pii import PIIScrubber
from staffeer.ports.profiles import ProfileParser
from staffeer.ports.reasoner import LLMReasoner, NullLLMReasoner
from staffeer.ports.semantic_index import NullSemanticIndex, SemanticIndex
from staffeer.ports.supply_demand import SupplyDemandSource


@dataclass(frozen=True)
class Matcher:
    """Orchestrates filter → score → rank → explain for one role."""

    supply: SupplyDemandSource
    profiles: ProfileParser
    feedback: FeedbackStore
    pii: PIIScrubber
    include_states: tuple[SupplyState, ...] = (SupplyState.BEACH,)
    weights: Mapping[str, float] = field(default_factory=dict)
    semantic_index: SemanticIndex = field(default_factory=NullSemanticIndex)
    reasoner: LLMReasoner = field(default_factory=NullLLMReasoner)

    def match(self, role: Role) -> Shortlist:
        """Return the ranked, explained shortlist for `role`, with explained exclusions."""
        screened = screen_consultants(self.supply.consultants(*self.include_states), role)
        matches = rank(self._match_for(result, role) for result in screened if result.eligible)
        excluded = tuple(result for result in screened if not result.eligible)
        return Shortlist(role=role, matches=matches, excluded=excluded)

    def _match_for(self, result: EligibilityResult, role: Role) -> Match:
        """Score and explain one eligible consultant against `role`."""
        coverage = skill_coverage(role, result.consultant)
        explanation = Explanation(factors=(*constraint_factors(result), skill_factor(coverage)))
        contribution = skill_contribution(coverage, self.weights.get("skills", 1.0))
        return assemble_match(result.consultant, (contribution,), explanation)
