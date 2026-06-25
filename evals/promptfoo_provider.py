"""Promptfoo exec provider — reads a scenario by id and runs the core matcher.

Promptfoo's exec provider passes the rendered prompt as the final CLI argument; when
run by hand the same payload may instead arrive as JSON on stdin (``{"prompt": ...}``).
Either way the prompt is the identity template ``scenario_id|role_description``.
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
from pathlib import Path

# Promptfoo runs this script from the config's directory (evals/), so the repo root is
# not on the import path. Add it from this file's own location (not the cwd) so the
# `evals` namespace package resolves regardless of where the provider is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.datasets.role_scenarios import ROLE_SCENARIOS  # noqa: E402

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource  # noqa: E402
from staffeer.adapters.null_feedback import NullFeedbackStore  # noqa: E402
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner  # noqa: E402
from staffeer.adapters.null_pii import NullPIIScrubber  # noqa: E402
from staffeer.adapters.null_profiles import NullProfileParser  # noqa: E402
from staffeer.adapters.null_semantic_index import NullSemanticIndex  # noqa: E402
from staffeer.domain.matcher import Matcher  # noqa: E402
from staffeer.domain.models import SupplyState  # noqa: E402


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


def _read_prompt() -> str:
    """Promptfoo's exec provider calls ``<cmd> <prompt> <options> <context>``, so the
    prompt is the first appended arg; fall back to stdin JSON when run by hand."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return json.loads(sys.stdin.read()).get("prompt", "")


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
        scenario_id, role_description = _parse_prompt(_read_prompt())
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid input: {exc}"}))
        sys.exit(1)
    try:
        result = run_scenario(scenario_id=scenario_id, role_description=role_description)
    except ProviderError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
    print(json.dumps(result))
