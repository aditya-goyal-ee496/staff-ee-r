"""Promptfoo exec provider — reads a scenario by id and runs the core matcher.

Reads JSON from stdin with keys ``scenario_id`` and optional ``role_description``.
Finds the scenario in ROLE_SCENARIOS, builds a Matcher with null adapters and an
InMemorySupplyDemandSource seeded with the scenario consultants, calls match(), then
prints a JSON result with shortlist, excluded, and rationale.

When ``role_description`` is supplied it overrides the role title so Promptfoo can
drive per-row role descriptions through the core (acceptance criterion).

No network I/O.  All imports are absolute staffeer imports.
"""

from __future__ import annotations

import json
import sys

from evals.datasets.role_scenarios import ROLE_SCENARIOS

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import SupplyState


class ProviderError(Exception):
    """Raised when the Promptfoo provider cannot fulfil a request."""


def _find_scenario(scenario_id: str) -> dict:
    for s in ROLE_SCENARIOS:
        if s["id"] == scenario_id:
            return s
    raise ProviderError(f"scenario not found: {scenario_id!r}")


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


def _rationale_for(shortlist) -> dict[str, list[str]]:
    return {
        m.consultant.name: [f.summary for f in m.explanation.factors] for m in shortlist.matches
    }


def _resolve_role(scenario: dict, role_description: str):
    """Return the scenario role, optionally with title overridden by role_description."""
    role = scenario["role"]
    if role_description:
        return role.model_copy(update={"title": role_description})
    return role


def _parse_prompt(prompt: str) -> tuple[str, str]:
    """Parse the identity prompt 'scenario_id|role_description' into parts."""
    parts = prompt.split("|", 1)
    scenario_id = parts[0].strip()
    role_description = parts[1].strip() if len(parts) > 1 else ""
    return scenario_id, role_description


def run_scenario(scenario_id: str, role_description: str) -> dict:
    """Find scenario, run matcher, return result dict."""
    scenario = _find_scenario(scenario_id)
    role = _resolve_role(scenario, role_description)
    shortlist = _build_matcher(scenario).match(role)
    return {
        "shortlist": [m.consultant.name for m in shortlist.matches],
        "excluded": [r.consultant.name for r in shortlist.excluded],
        "rationale": _rationale_for(shortlist),
    }


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        scenario_id, role_description = _parse_prompt(payload.get("prompt", ""))
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid input: {exc}"}))
        sys.exit(1)
    try:
        result = run_scenario(scenario_id=scenario_id, role_description=role_description)
    except ProviderError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
    print(json.dumps(result))
