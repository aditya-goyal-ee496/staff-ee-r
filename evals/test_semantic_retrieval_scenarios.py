"""Deterministic golden-table SCENARIO EVALS — Slice 05: Semantic retrieval (Milvus Lite).

Each scenario is a frozen fixture asserting the exact behaviour of semantic scoring and
explanation functions against known inputs. The suite uses no network I/O.

Scenarios
---------
1. semantic_contribution_no_hits_yields_zero
   No hits -> ScoreContribution.value == 0.0.

2. semantic_contribution_max_score_wins
   Multiple hits -> value equals the highest similarity score.

3. semantic_contribution_source_label
   Source is always "semantic" (canonical label).

4. semantic_contribution_custom_weight_is_applied
   weight=0.5 -> weighted == value * 0.5.

5. semantic_factor_empty_hits_reports_no_matches
   Empty hits -> ExplanationFactor.summary contains "no semantic matches found".

6. semantic_factor_shows_top_score_in_summary
   Hits present -> summary includes the top score value.

7. [NEGATIVE] semantic_contribution_all_zero_scores_still_yields_zero_value
   All hits have score=0.0 -> value is 0.0, NOT fabricated.
   This NEGATIVE scenario confirms the implementation never invents a positive signal.
   A 100% pass rate without this scenario is a COVERAGE WARNING.

NOTE: A 100% pass rate across all scenarios (including scenario 7) is expected and correct;
what would be a WARNING is *omitting* the negative scenario — that signals insufficient coverage.
"""

from __future__ import annotations

import pytest

from staffeer.domain.explain import semantic_factor
from staffeer.domain.ranking import semantic_contribution
from staffeer.ports.semantic_index import Hit

# ---------------------------------------------------------------------------
# Scenario 1 — no hits yields value 0.0
# ---------------------------------------------------------------------------


def test_semantic_contribution_no_hits_yields_zero() -> None:
    """No hits -> ScoreContribution.value == 0.0."""
    # Arrange
    hits: list[Hit] = []
    # Act
    contribution = semantic_contribution(hits)
    # Assert
    assert contribution.value == 0.0


# ---------------------------------------------------------------------------
# Scenario 2 — max score wins
# ---------------------------------------------------------------------------


def test_semantic_contribution_max_score_wins() -> None:
    """Multiple hits -> value equals the maximum similarity score."""
    # Arrange
    hits = [
        Hit(id="C-01", score=0.5, text="python"),
        Hit(id="C-02", score=0.95, text="python django"),
        Hit(id="C-03", score=0.2, text="java"),
    ]
    # Act
    contribution = semantic_contribution(hits)
    # Assert
    assert contribution.value == 0.95


# ---------------------------------------------------------------------------
# Scenario 3 — source label is "semantic"
# ---------------------------------------------------------------------------


def test_semantic_contribution_source_label() -> None:
    """Source label is always the canonical string 'semantic'."""
    # Arrange
    hits = [Hit(id="C-01", score=0.7, text="python")]
    # Act
    contribution = semantic_contribution(hits)
    # Assert
    assert contribution.source == "semantic"


# ---------------------------------------------------------------------------
# Scenario 4 — custom weight is applied
# ---------------------------------------------------------------------------


def test_semantic_contribution_custom_weight_is_applied() -> None:
    """weight=0.5 is reflected in contribution.weighted."""
    # Arrange
    hits = [Hit(id="C-01", score=0.8, text="python")]
    # Act
    contribution = semantic_contribution(hits, weight=0.5)
    # Assert
    assert contribution.weighted == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Scenario 5 — semantic_factor empty hits
# ---------------------------------------------------------------------------


def test_semantic_factor_empty_hits_reports_no_matches() -> None:
    """Empty hits list -> factor summary says 'no semantic matches found'."""
    # Arrange
    hits: list[Hit] = []
    # Act
    factor = semantic_factor(hits)
    # Assert
    assert "no semantic matches found" in factor.summary


# ---------------------------------------------------------------------------
# Scenario 6 — semantic_factor shows top score
# ---------------------------------------------------------------------------


def test_semantic_factor_shows_top_score_in_summary() -> None:
    """Hits present -> factor summary includes the top similarity score."""
    # Arrange
    hits = [
        Hit(id="C-01", score=0.88, text="python django web"),
        Hit(id="C-02", score=0.3, text="java backend"),
    ]
    # Act
    factor = semantic_factor(hits)
    # Assert
    assert "0.88" in factor.summary


# ---------------------------------------------------------------------------
# Scenario 7 — NEGATIVE: all-zero scores never fabricate a positive signal
#
# This is the mandatory NEGATIVE scenario. Its presence prevents a 100%-green
# suite from masking a missing guard. If semantic_contribution ever returned
# a value > 0.0 when all hit scores are 0.0, this test would fail — which is
# exactly what we want.
# ---------------------------------------------------------------------------


def test_semantic_contribution_all_zero_scores_still_yields_zero_value() -> None:
    """NEGATIVE: hits with score=0.0 must not fabricate a positive value."""
    # Arrange
    hits = [
        Hit(id="C-01", score=0.0, text="python"),
        Hit(id="C-02", score=0.0, text="java"),
    ]
    # Act
    contribution = semantic_contribution(hits)
    # Assert — must not invent signal where none exists
    assert contribution.value == 0.0
