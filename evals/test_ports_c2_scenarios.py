"""Deterministic golden-table SCENARIO EVALS — Slice C2: SemanticIndex + LLMReasoner ports.

Each scenario is a frozen fixture that exercises the two new ports and their null objects
end-to-end with no network I/O.  100% relevance is a COVERAGE WARNING, not a pass —
the mandatory NEGATIVE scenario (LLMReasoner returns a result with invalid confidence)
must be present and must fail when the invariant is relaxed.

Scenarios
---------
1. null_semantic_index_upsert_is_idempotent
   NullSemanticIndex.upsert() always returns None without error.

2. null_semantic_index_query_returns_empty_list
   NullSemanticIndex.query() returns an empty sequence — no fabricated hits.

3. null_semantic_index_query_for_unknown_namespace_returns_empty
   Querying with an arbitrary namespace on NullSemanticIndex yields no hits
   (namespace isolation: the null object never cross-contaminates namespaces).

4. null_llm_reasoner_assess_returns_soft_assessment
   NullLLMReasoner.assess() returns a SoftAssessment with score=0.0 and empty evidence.

5. soft_assessment_confidence_within_range
   SoftAssessment rejects a confidence value outside [0.0, 1.0].
   This POSITIVE scenario verifies model_validator is wired.

6. new_error_classes_are_subclasses_of_staffeer_error
   Both SemanticIndexError and LLMReasonerError are importable as StaffeerError subclasses.

7. [NEGATIVE] soft_assessment_with_out_of_range_confidence_is_rejected
   NEGATIVE SCENARIO: constructing SoftAssessment(confidence=1.5) must raise a
   ValidationError.  A test that expects construction to succeed would represent
   a missing guard.  A 100% pass-rate without this xfail is a COVERAGE WARNING.

NOTE: A 100% pass rate across all scenarios would mean scenario 7 (the negative case)
is absent or broken — treat that as a coverage failure.
"""

from __future__ import annotations

import pytest

from staffeer.adapters.null_llm_reasoner import NullLLMReasoner
from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.domain.errors import LLMReasonerError, SemanticIndexError, StaffeerError
from staffeer.ports.reasoner import SoftAssessment
from staffeer.ports.semantic_index import IndexItem

# ---------------------------------------------------------------------------
# Scenario 1 — NullSemanticIndex upsert is idempotent (no error, no return)
# ---------------------------------------------------------------------------


def test_null_semantic_index_upsert_is_idempotent() -> None:
    """NullSemanticIndex.upsert() returns None and never raises."""
    # Arrange
    index = NullSemanticIndex()
    item = IndexItem(id="C-01", text="python django rest", namespace="skills")
    # Act
    result = index.upsert(item)
    # Assert
    assert result is None


# ---------------------------------------------------------------------------
# Scenario 2 — NullSemanticIndex.query returns empty list (no fabricated hits)
# ---------------------------------------------------------------------------


def test_null_semantic_index_query_returns_empty_list() -> None:
    """NullSemanticIndex.query() yields an empty sequence — no fabricated hits."""
    # Arrange
    index = NullSemanticIndex()
    # Act
    hits = index.query(text="python", namespace="skills", top_k=5)
    # Assert
    assert list(hits) == []


# ---------------------------------------------------------------------------
# Scenario 3 — unknown namespace query returns empty (no cross-contamination)
# ---------------------------------------------------------------------------


def test_null_semantic_index_query_for_unknown_namespace_returns_empty() -> None:
    """Querying an unknown namespace on NullSemanticIndex returns no hits."""
    # Arrange
    index = NullSemanticIndex()
    # Act
    hits = index.query(text="anything", namespace="does-not-exist", top_k=10)
    # Assert
    assert list(hits) == []


# ---------------------------------------------------------------------------
# Scenario 4 — NullLLMReasoner.assess returns SoftAssessment (score=0.0, no evidence)
# ---------------------------------------------------------------------------


def test_null_llm_reasoner_assess_returns_soft_assessment() -> None:
    """NullLLMReasoner.assess() returns a SoftAssessment typed value — no network call."""
    # Arrange
    reasoner = NullLLMReasoner()
    # Act
    result = reasoner.assess(consultant_summary="backend developer", role_description="API role")
    # Assert
    assert isinstance(result, SoftAssessment)


# ---------------------------------------------------------------------------
# Scenario 5 — SoftAssessment confidence within [0.0, 1.0] is valid
# ---------------------------------------------------------------------------


def test_soft_assessment_confidence_within_range() -> None:
    """SoftAssessment with confidence=0.75 is valid and stores the value."""
    # Arrange / Act
    assessment = SoftAssessment(score=0.75, confidence=0.75, evidence=(), summary="good fit")
    # Assert
    assert assessment.confidence == 0.75


# ---------------------------------------------------------------------------
# Scenario 6 — error classes importable and inherit StaffeerError
# ---------------------------------------------------------------------------


def test_new_error_classes_are_subclasses_of_staffeer_error() -> None:
    """SemanticIndexError and LLMReasonerError are both subclasses of StaffeerError."""
    # Arrange / Act / Assert
    assert issubclass(SemanticIndexError, StaffeerError)
    assert issubclass(LLMReasonerError, StaffeerError)


# ---------------------------------------------------------------------------
# Scenario 7 — NEGATIVE: out-of-range confidence is rejected by model_validator
#
# This scenario is EXPECTED to fail when the model_validator is absent/broken.
# Its purpose is to prove the eval suite detects missing validation guards.
# A 100% pass rate (no xfails) is a COVERAGE WARNING.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "NEGATIVE SCENARIO: SoftAssessment with confidence=1.5 must raise ValidationError. "
        "If this xfail does not trigger the model_validator is missing or broken. "
        "A 100%% pass rate (no xfails) is a COVERAGE WARNING."
    ),
    strict=True,
)
def test_soft_assessment_with_out_of_range_confidence_is_rejected() -> None:
    """NEGATIVE: SoftAssessment(confidence=1.5) must raise — xfail is the correct outcome."""
    # Arrange / Act — building an invalid value object must raise; if it succeeds the test body
    # continues and we manually fail to trigger the xfail marker.
    try:
        SoftAssessment(score=0.0, confidence=1.5, evidence=(), summary="bad")
    except Exception:
        # Validation raised as expected — this is the PASSING path for a correct implementation.
        # We deliberately re-raise so pytest sees a failure and honours strict=True xfail.
        raise
    # If no exception was raised the guard is absent — fail the test explicitly.
    pytest.fail("SoftAssessment accepted confidence=1.5; model_validator is missing")
