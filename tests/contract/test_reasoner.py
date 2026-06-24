"""Contract suite for the `LLMReasoner` port (spec: docs/tasks/00b-contracts.md, C2-03).

Nine one-assertion tests verifying the structural invariants that every LLMReasoner
implementation must satisfy.  Exercised against NullLLMReasoner and StubLLMReasoner so
the entire suite runs with no network I/O.

AAA layout — Arrange / Act / Assert — one assertion per test.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from staffeer.ports.reasoner import (
    Evidence,
    LLMReasoner,
    NullLLMReasoner,
    SoftAssessment,
)

# ---------------------------------------------------------------------------
# Stub — deterministic stand-in used for interface-level tests
# ---------------------------------------------------------------------------


class StubLLMReasoner:
    """Returns a fixed SoftAssessment with non-zero score and one evidence item."""

    def assess(self, *, consultant_summary: str, role_description: str) -> SoftAssessment:
        evidence = (Evidence(source="stub", claim="strong match"),)
        return SoftAssessment(score=0.8, confidence=0.9, evidence=evidence, summary="good fit")


@pytest.fixture
def null_reasoner() -> LLMReasoner:
    return NullLLMReasoner()


@pytest.fixture
def stub_reasoner() -> StubLLMReasoner:
    return StubLLMReasoner()


# T1 — NullLLMReasoner satisfies the LLMReasoner protocol
def test_null_reasoner_satisfies_the_port(null_reasoner: LLMReasoner) -> None:
    assert isinstance(null_reasoner, LLMReasoner)


# T2 — NullLLMReasoner.assess returns SoftAssessment
def test_null_reasoner_assess_returns_soft_assessment(null_reasoner: LLMReasoner) -> None:
    # Arrange / Act
    result = null_reasoner.assess(
        consultant_summary="backend developer", role_description="API role"
    )
    # Assert
    assert isinstance(result, SoftAssessment)


# T3 — NullLLMReasoner returns score=0.0 (no fabricated scores)
def test_null_reasoner_returns_zero_score(null_reasoner: LLMReasoner) -> None:
    # Arrange / Act
    result = null_reasoner.assess(
        consultant_summary="backend developer", role_description="API role"
    )
    # Assert
    assert result.score == 0.0


# T4 — NullLLMReasoner returns empty evidence (no fabricated claims)
def test_null_reasoner_returns_empty_evidence(null_reasoner: LLMReasoner) -> None:
    # Arrange / Act
    result = null_reasoner.assess(
        consultant_summary="backend developer", role_description="API role"
    )
    # Assert
    assert result.evidence == ()


# T5 — StubLLMReasoner returns non-zero score
def test_stub_reasoner_returns_non_zero_score(stub_reasoner: StubLLMReasoner) -> None:
    # Arrange / Act
    result = stub_reasoner.assess(
        consultant_summary="backend developer", role_description="API role"
    )
    # Assert
    assert result.score > 0.0


# T6 — StubLLMReasoner returns at least one evidence item
def test_stub_reasoner_returns_evidence(stub_reasoner: StubLLMReasoner) -> None:
    # Arrange / Act
    result = stub_reasoner.assess(
        consultant_summary="backend developer", role_description="API role"
    )
    # Assert
    assert len(result.evidence) > 0


# T7a — Evidence carries source field
def test_evidence_carries_source() -> None:
    # Arrange / Act
    evidence = Evidence(source="profile", claim="has 3 years Python")
    # Assert
    assert evidence.source == "profile"


# T7b — Evidence carries claim field
def test_evidence_carries_claim() -> None:
    # Arrange / Act
    evidence = Evidence(source="profile", claim="has 3 years Python")
    # Assert
    assert evidence.claim == "has 3 years Python"


# T8 — SoftAssessment rejects confidence outside [0.0, 1.0]
def test_soft_assessment_rejects_out_of_range_confidence() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValidationError):
        SoftAssessment(score=0.0, confidence=1.5, evidence=(), summary="bad")


# T9 — StubLLMReasoner satisfies the LLMReasoner protocol
def test_stub_reasoner_satisfies_the_port(stub_reasoner: StubLLMReasoner) -> None:
    assert isinstance(stub_reasoner, LLMReasoner)


# T10 — NullLLMReasoner sets abstained=True
def test_null_reasoner_abstains(null_reasoner: LLMReasoner) -> None:
    # Arrange / Act
    result = null_reasoner.assess(
        consultant_summary="backend developer", role_description="API role"
    )
    # Assert
    assert result.abstained is True


# T11 — abstaining response has empty cited_sources
def test_null_reasoner_returns_empty_cited_sources(null_reasoner: LLMReasoner) -> None:
    # Arrange / Act
    result = null_reasoner.assess(
        consultant_summary="backend developer", role_description="API role"
    )
    # Assert
    assert result.cited_sources == ()


# T12 — non-abstaining SoftAssessment with empty summary raises ValidationError
def test_non_abstaining_with_empty_summary_raises_validation_error() -> None:
    # Arrange / Act / Assert
    with pytest.raises(ValidationError):
        SoftAssessment(score=0.5, confidence=0.8, abstained=False, summary="")
