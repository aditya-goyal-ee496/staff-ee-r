"""DeepEval faithfulness suite — heavy lane only (needs eval extra + API key).

For each positive scenario: builds a Matcher with null adapters, calls match(), builds
a rationale dict (name → factor summaries), builds a profile string from consultant
skills, then asserts FaithfulnessMetric scores at or above 0.6.

NOTE: A score of 1.0 on all tests is a COVERAGE WARNING, not a success signal (ADR-001).
      If the suite passes 100%, add scenarios with richer, less trivially-verifiable rationale.
"""

from __future__ import annotations

import pytest

# importorskip on deepeval.metrics.g_eval (not the local package) to skip when PyPI deepeval
# is absent.  The local evals/deepeval/ package would satisfy a plain "deepeval" skip check.
pytest.importorskip("deepeval.metrics.g_eval")

pytestmark = pytest.mark.integration

import sys  # noqa: E402

sys.path.insert(0, ".")

from evals.datasets.role_scenarios import ROLE_SCENARIOS  # noqa: E402
from evals.deepeval.metrics import FaithfulnessMetric  # noqa: E402

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


def _profile_text(consultant) -> str:
    return f"{consultant.name} ({consultant.location}): {', '.join(consultant.skills)}"


@pytest.mark.parametrize("scenario", _POSITIVE, ids=lambda s: s["id"])
def test_rationale_faithfulness_above_threshold(scenario: dict) -> None:
    """Positive scenario rationale must score at least 0.6 for faithfulness."""
    shortlist = _build_matcher(scenario).match(scenario["role"])
    assert shortlist.matches, "positive scenario produced empty shortlist"
    rationale = {
        m.consultant.name: [f.summary for f in m.explanation.factors] for m in shortlist.matches
    }
    profiles = " | ".join(_profile_text(c) for c in scenario["consultants"])
    score = FaithfulnessMetric(threshold=0.6).measure(rationale, profiles)
    assert score >= 0.6


def test_faithfulness_score_is_not_one_for_negative_scenario() -> None:
    """Negative scenario faithfulness must not equal 1.0 — that is a coverage warning."""
    scenario = _NEGATIVE[3]
    shortlist = _build_matcher(scenario).match(scenario["role"])
    rationale = {
        m.consultant.name: [f.summary for f in m.explanation.factors] for m in shortlist.matches
    }
    profiles = " | ".join(_profile_text(c) for c in scenario["consultants"])
    score = FaithfulnessMetric(threshold=0.6).measure(rationale, profiles)
    assert score != 1.0, "Score of 1.0 on a negative scenario is a coverage warning"
