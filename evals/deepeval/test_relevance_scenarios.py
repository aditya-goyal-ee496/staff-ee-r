"""DeepEval relevance suite — heavy lane only (needs eval extra + API key).

Parametrizes positive scenarios from ROLE_SCENARIOS.  Each test builds a Matcher with
null adapters, runs match(), and asserts RelevanceMetric scores at or above threshold.

NOTE: A score of 1.0 on all tests is a COVERAGE WARNING, not a success signal (ADR-001).
      If the suite passes 100%, add harder scenarios with more ambiguous skill overlaps.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("deepeval")

pytestmark = pytest.mark.integration

# Anchor path to project root so the suite is portable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evals.datasets.role_scenarios import ROLE_SCENARIOS  # noqa: E402
from evals.deepeval.metrics import RelevanceMetric  # noqa: E402

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource  # noqa: E402
from staffeer.adapters.null_feedback import NullFeedbackStore  # noqa: E402
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner  # noqa: E402
from staffeer.adapters.null_pii import NullPIIScrubber  # noqa: E402
from staffeer.adapters.null_profiles import NullProfileParser  # noqa: E402
from staffeer.adapters.null_semantic_index import NullSemanticIndex  # noqa: E402
from staffeer.domain.matcher import Matcher  # noqa: E402
from staffeer.domain.models import SupplyState  # noqa: E402

_POSITIVE = [s for s in ROLE_SCENARIOS if s["label"] == "positive"]
_NEGATIVE = [s for s in ROLE_SCENARIOS if s["label"] == "negative"]


def _build_matcher(scenario: dict) -> Matcher:
    return Matcher(
        supply=InMemorySupplyDemandSource(consultants=scenario["consultants"]),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=NullSemanticIndex(),
        reasoner=NullLLMReasoner(),
        include_states=(SupplyState.BEACH, SupplyState.ROLLING_OFF, SupplyState.NEW_JOINER),
    )


@pytest.mark.parametrize("scenario", _POSITIVE, ids=lambda s: s["id"])
def test_shortlist_relevance_above_threshold(scenario: dict) -> None:
    """Positive scenario shortlist must score at least 0.7 for relevance."""
    shortlist = _build_matcher(scenario).match(scenario["role"])
    names = [m.consultant.name for m in shortlist.matches]
    role_text = f"{scenario['role'].title}: {', '.join(scenario['role'].required_skills)}"
    score = RelevanceMetric(threshold=0.7).measure(names, role_text)
    assert score >= 0.7


def test_relevance_score_is_below_one_for_negative_scenario() -> None:
    """Negative scenario relevance must be below 1.0 — 1.0 is a coverage warning."""
    if len(_NEGATIVE) < 1:
        pytest.skip("No negative scenarios defined in ROLE_SCENARIOS")
    scenario = _NEGATIVE[0]
    shortlist = _build_matcher(scenario).match(scenario["role"])
    names = [m.consultant.name for m in shortlist.matches]
    role_text = f"{scenario['role'].title}: {', '.join(scenario['role'].required_skills)}"
    score = RelevanceMetric(threshold=0.7).measure(names, role_text)
    assert score < 1.0, "Score of 1.0 on a negative scenario is a coverage warning"
