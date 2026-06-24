"""Matcher pipeline behaviour: eligible consultants ranked by fit, exclusions explained."""

from __future__ import annotations

from collections.abc import Sequence

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import Consultant, Role
from staffeer.ports.reasoner import Evidence, LLMReasoner, SoftAssessment


class _StubLLMReasoner:
    """Deterministic stub — returns score=0.8 with one evidence item, no network."""

    def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
        evidence = (Evidence(source="stub-profile", claim="strong match"),)
        return SoftAssessment(
            score=0.8,
            confidence=0.9,
            evidence=evidence,
            cited_sources=("stub-profile",),
            summary="Stub: strong fit for the role.",
        )


def _matcher(consultants: Sequence[Consultant]) -> Matcher:
    return Matcher(
        supply=InMemorySupplyDemandSource(consultants=consultants),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=NullSemanticIndex(),
        reasoner=NullLLMReasoner(),
    )


def _matcher_with_reasoner(
    consultants: Sequence[Consultant],
    reasoner: LLMReasoner | None = None,
) -> Matcher:
    """Build a Matcher with an optional custom reasoner (defaults to NullLLMReasoner)."""
    return Matcher(
        supply=InMemorySupplyDemandSource(consultants=consultants),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=NullSemanticIndex(),
        reasoner=reasoner or NullLLMReasoner(),
    )


def _remote_role() -> Role:
    return Role(
        id="R-01", title="Engineer", location="Remote-India", required_skills=("python", "sql")
    )


def test_consultant_with_fuller_skill_coverage_ranks_first() -> None:
    asha = Consultant(id="C-01", name="Asha", location="Chennai", skills=("python", "sql"))
    bina = Consultant(id="C-02", name="Bina", location="Bengaluru", skills=("python",))
    shortlist = _matcher((bina, asha)).match(_remote_role())
    assert shortlist.matches[0].consultant.name == "Asha"


def test_location_ineligible_consultant_is_excluded_with_its_reason() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", required_skills=("python",))
    pune = Consultant(id="C-01", name="Imran", location="Pune", skills=("python",))
    shortlist = _matcher((pune,)).match(role)
    assert shortlist.excluded[0].failures[0].name == "location"


def test_an_eligible_match_carries_a_skill_explanation_factor() -> None:
    asha = Consultant(id="C-01", name="Asha", location="Chennai", skills=("python", "sql"))
    shortlist = _matcher((asha,)).match(_remote_role())
    assert any(factor.source == "skills" for factor in shortlist.matches[0].explanation.factors)


def test_no_eligible_consultant_yields_no_matches() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", required_skills=("python",))
    pune = Consultant(id="C-01", name="Imran", location="Pune", skills=("python",))
    assert _matcher((pune,)).match(role).matches == ()


# ---------------------------------------------------------------------------
# Soft scoring tests (I06-12) — StubLLMReasoner and NullLLMReasoner
# ---------------------------------------------------------------------------


def _asha() -> Consultant:
    return Consultant(id="C-01", name="Asha", location="Chennai", skills=("python", "sql"))


def _remote_role() -> Role:
    return Role(
        id="R-01", title="Engineer", location="Remote-India", required_skills=("python", "sql")
    )


def test_soft_score_matched_consultant_has_soft_llm_score_contribution() -> None:
    # Arrange
    shortlist = _matcher_with_reasoner((_asha(),), _StubLLMReasoner()).match(_remote_role())
    match = shortlist.matches[0]
    # Assert
    assert any(c.source == "soft_llm" for c in match.contributions)


def test_soft_score_stub_contribution_value_is_0_8() -> None:
    # Arrange
    shortlist = _matcher_with_reasoner((_asha(),), _StubLLMReasoner()).match(_remote_role())
    match = shortlist.matches[0]
    soft_contributions = [c for c in match.contributions if c.source == "soft_llm"]
    # Assert
    assert soft_contributions[0].value == 0.8


def test_null_reasoner_soft_llm_factor_summary_starts_with_llm_abstained() -> None:
    # Arrange — NullLLMReasoner abstains; factor must say so
    shortlist = _matcher_with_reasoner((_asha(),), NullLLMReasoner()).match(_remote_role())
    match = shortlist.matches[0]
    soft_factors = [f for f in match.explanation.factors if f.source == "soft_llm"]
    # Assert
    assert soft_factors[0].summary.startswith("LLM abstained")


def test_stub_reasoner_match_score_exceeds_null_reasoner_match_score() -> None:
    # Arrange
    null_score = _matcher_with_reasoner((_asha(),)).match(_remote_role()).matches[0].score
    stub_score = (
        _matcher_with_reasoner((_asha(),), _StubLLMReasoner())
        .match(_remote_role())
        .matches[0]
        .score
    )
    # Assert
    assert stub_score > null_score
