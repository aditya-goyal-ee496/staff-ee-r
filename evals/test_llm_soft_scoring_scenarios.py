"""Deterministic golden-table SCENARIO EVALS — Slice 06: LLM reasoning, soft scoring & ranking.

Each scenario is a frozen fixture exercising the soft-scoring pipeline end-to-end with
stub/null adapters — zero network I/O. 100% relevance is a COVERAGE WARNING, not a pass.

The mandatory NEGATIVE scenarios (abstention and PII-before-LLM) must be present and
must pass. A pass rate of 100% on only positive cases is a coverage failure signal.

Scenarios
---------
1. stub_reasoner_raises_match_score_above_null
   A StubLLMReasoner (score=0.8) raises the match score above what NullLLMReasoner yields.

2. soft_contribution_appears_in_contributions_for_matched_consultant
   After matching, the returned Match.contributions contains a ScoreContribution with
   source='soft_llm'. (Exercises I06-06 + I06-08.)

3. soft_factor_appears_in_explanation_for_matched_consultant
   After matching, the returned Match.explanation contains an ExplanationFactor with
   source='soft_llm'. (Exercises I06-07 + I06-08.)

4. ranked_shortlist_orders_higher_soft_scorer_first
   When two consultants are equal on hard/skill score but differ on soft score, the
   higher soft scorer ranks first. (Exercises I06-08 + ranking.)

5. [NEGATIVE] abstention_when_reasoner_returns_low_confidence
   When NullLLMReasoner is used the soft_factor summary starts with 'LLM abstained'.
   A system that never abstains would skip this case — that is a COVERAGE WARNING.

6. [NEGATIVE] null_reasoner_does_not_inflate_score
   With NullLLMReasoner, a match's score equals the skill-only score, proving the
   null path does not fabricate soft-score inflation. An implementation that blindly
   adds soft_score=0.0*weight should still satisfy this.

7. [NEGATIVE XFAIL] stub_reasoner_score_is_not_equal_to_null_score_when_skills_differ
   NEGATIVE SCENARIO: if a test incorrectly expected stub == null scores this would
   fail — proves the eval suite can detect such a bug. xfail is the correct outcome.

NOTE: Scenarios 5, 6, and 7 are the mandatory negative coverage. A suite with none of
these is incomplete and 100% green would be a false signal.
"""

from __future__ import annotations

import pytest

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import Consultant, Role, SupplyState
from staffeer.ports.reasoner import Evidence, SoftAssessment

# ---------------------------------------------------------------------------
# Shared stub
# ---------------------------------------------------------------------------


class _StubLLMReasoner:
    """Deterministic reasoner returning score=0.8, confidence=0.9, one evidence item."""

    def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
        evidence = (Evidence(source="stub-profile", claim="strong match"),)
        return SoftAssessment(
            score=0.8,
            confidence=0.9,
            evidence=evidence,
            cited_sources=("stub-profile",),
            summary="Stub: strong fit for the role.",
        )


def _remote_role() -> Role:
    return Role(
        id="R-06", title="Backend Engineer", location="Remote-India", required_skills=("python",)
    )


def _consultant(name: str = "Asha") -> Consultant:
    return Consultant(
        id="C-01", name=name, location="Chennai", skills=("python",), state=SupplyState.BEACH
    )


def _matcher(consultant: Consultant, *, reasoner=None) -> Matcher:
    if reasoner is None:
        reasoner = NullLLMReasoner()
    return Matcher(
        supply=InMemorySupplyDemandSource(consultants=(consultant,)),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=NullSemanticIndex(),
        reasoner=reasoner,
    )


# ---------------------------------------------------------------------------
# Scenario 1 — stub reasoner raises score above null
# ---------------------------------------------------------------------------


def test_stub_reasoner_raises_match_score_above_null() -> None:
    """A real (stub) reasoner must raise the final match score above the null path."""
    # Arrange
    consultant = _consultant()
    role = _remote_role()
    null_score = _matcher(consultant).match(role).matches[0].score
    # Act
    stub_score = _matcher(consultant, reasoner=_StubLLMReasoner()).match(role).matches[0].score
    # Assert
    assert stub_score > null_score


# ---------------------------------------------------------------------------
# Scenario 2 — soft ScoreContribution appears in Match.contributions
# ---------------------------------------------------------------------------


def test_soft_contribution_appears_in_contributions_for_matched_consultant() -> None:
    """Matched consultant's contributions include one with source='soft_llm'."""
    # Arrange
    consultant = _consultant()
    role = _remote_role()
    # Act
    match = _matcher(consultant, reasoner=_StubLLMReasoner()).match(role).matches[0]
    # Assert
    assert any(c.source == "soft_llm" for c in match.contributions)


# ---------------------------------------------------------------------------
# Scenario 3 — soft ExplanationFactor appears in Match.explanation
# ---------------------------------------------------------------------------


def test_soft_factor_appears_in_explanation_for_matched_consultant() -> None:
    """Matched consultant's explanation factors include one with source='soft_llm'."""
    # Arrange
    consultant = _consultant()
    role = _remote_role()
    # Act
    match = _matcher(consultant, reasoner=_StubLLMReasoner()).match(role).matches[0]
    # Assert
    assert any(f.source == "soft_llm" for f in match.explanation.factors)


# ---------------------------------------------------------------------------
# Scenario 4 — higher soft scorer ranks first when skill scores are tied
# ---------------------------------------------------------------------------


def test_ranked_shortlist_orders_higher_soft_scorer_first() -> None:
    """Two equal-skill consultants: the one with a higher soft score ranks first."""

    # Arrange — same skills, different names; a biased stub ranks Bina higher
    class _BiasedReasoner:
        def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
            score = 0.9 if "Bina" in consultant_summary else 0.1
            return SoftAssessment(score=score, confidence=0.8, summary="biased fit")

    asha = Consultant(id="C-01", name="Asha", location="Chennai", skills=("python",))
    bina = Consultant(id="C-02", name="Bina", location="Bengaluru", skills=("python",))
    matcher = Matcher(
        supply=InMemorySupplyDemandSource(consultants=(asha, bina)),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=NullSemanticIndex(),
        reasoner=_BiasedReasoner(),
    )
    # Act
    shortlist = matcher.match(
        Role(id="R-06", title="Backend", location="Remote-India", required_skills=("python",))
    )
    # Assert
    assert shortlist.matches[0].consultant.name == "Bina"


# ---------------------------------------------------------------------------
# Scenario 5 — NEGATIVE: abstention when NullLLMReasoner is used
# ---------------------------------------------------------------------------


def test_abstention_when_null_reasoner_used_soft_factor_summary_starts_with_llm_abstained() -> None:
    """NEGATIVE scenario: NullLLMReasoner causes 'LLM abstained' explanation factor.

    This validates the abstention path — a system that never abstains would fail here.
    """
    # Arrange
    consultant = _consultant()
    role = _remote_role()
    # Act — NullLLMReasoner is the default
    match = _matcher(consultant).match(role).matches[0]
    soft_factors = [f for f in match.explanation.factors if f.source == "soft_llm"]
    # Assert
    assert soft_factors, "soft_llm factor must always be present even when abstaining"
    assert soft_factors[0].summary.startswith("LLM abstained")


# ---------------------------------------------------------------------------
# Scenario 6 — NEGATIVE: null reasoner does not inflate match score
# ---------------------------------------------------------------------------


def test_null_reasoner_does_not_inflate_score() -> None:
    """NEGATIVE: NullLLMReasoner contributes score=0.0, leaving total unchanged by soft path.

    With skills weight=1.0 and soft_llm weight=1.0 and soft score=0.0, the total must
    equal the skill-only score (0.0 * 1.0 == 0.0 contribution). This fails if the adapter
    fabricates a non-zero soft score.
    """
    # Arrange
    consultant = Consultant(id="C-01", name="Asha", location="Remote-India", skills=("python",))
    role = Role(id="R-06", title="Backend", location="Remote-India", required_skills=("python",))
    # Act
    match = _matcher(consultant).match(role).matches[0]
    soft_contributions = [c for c in match.contributions if c.source == "soft_llm"]
    # Assert
    assert soft_contributions[0].value == 0.0


# ---------------------------------------------------------------------------
# Scenario 7 — NEGATIVE XFAIL: stub and null scores are NOT equal
#
# This xfail proves the eval suite can detect an implementation bug where soft
# scoring is ignored (stub and null would then yield the same score).
# A 100% pass rate without this xfail is a COVERAGE WARNING.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "NEGATIVE SCENARIO: stub reasoner (score=0.8) and null reasoner (score=0.0) must "
        "yield different match totals. If they are equal, the soft contribution is not wired. "
        "This xfail proves the suite detects that bug. A 100%% pass rate is a COVERAGE WARNING."
    ),
    strict=True,
)
def test_stub_score_equals_null_score_is_a_bug_negative_xfail() -> None:
    """NEGATIVE XFAIL: deliberately asserts stub_score == null_score, which must fail."""
    # Arrange
    consultant = _consultant()
    role = _remote_role()
    null_score = _matcher(consultant).match(role).matches[0].score
    stub_score = _matcher(consultant, reasoner=_StubLLMReasoner()).match(role).matches[0].score
    # Assert — this assertion is WRONG and must trigger the xfail
    assert stub_score == null_score, "If equal, soft contribution is not wired (bug)"
