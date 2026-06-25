"""Coverage-contract guard — deterministic, no integration mark.

Enforces the minimum scenario counts that keep the eval harness honest.
A relevance or faithfulness suite scoring 100% is a COVERAGE WARNING (ADR-001):
full marks signal the suite is too easy, not that the system is perfect.
Having at least 4 negative and 2 positive scenarios is a structural guard against
an accidentally trivial test suite.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

import pytest
from evals.datasets.role_scenarios import ROLE_SCENARIOS


def test_negative_scenario_count_is_at_least_four() -> None:
    """At least 4 negative scenarios must exist because 100% pass rate is a coverage warning
    (ADR-001), not a success signal — fewer negatives make a trivially-easy suite."""
    negative_count = sum(1 for s in ROLE_SCENARIOS if s["label"] == "negative")
    assert negative_count >= 4, (
        f"Only {negative_count} negative scenarios found; need at least 4. "
        "A 100% pass rate is a coverage warning — add harder negative cases."
    )


def test_positive_scenario_count_is_at_least_two() -> None:
    """At least 2 positive scenarios must exist to verify real matches are surfaced."""
    positive_count = sum(1 for s in ROLE_SCENARIOS if s["label"] == "positive")
    assert positive_count >= 2, f"Only {positive_count} positive scenarios found; need at least 2."


@pytest.mark.parametrize("scenario", ROLE_SCENARIOS, ids=lambda s: s["id"])
def test_expected_includes_are_subset_of_consultants(scenario: dict) -> None:
    """Every name in expected_includes must exist as a consultant in the same scenario.

    Guards against dataset drift where a name is asserted but the consultant was
    renamed or removed, leaving expected_includes silently unreachable.
    """
    consultant_names = {c.name for c in scenario["consultants"]}
    for name in scenario["expected_includes"]:
        assert name in consultant_names, (
            f"Scenario {scenario['id']!r}: expected_includes names {name!r} "
            f"but no consultant with that name exists in the scenario."
        )


@pytest.mark.parametrize("scenario", ROLE_SCENARIOS, ids=lambda s: s["id"])
def test_expected_excludes_are_subset_of_consultants(scenario: dict) -> None:
    """Every name in expected_excludes must exist as a consultant in the same scenario.

    Guards against dataset drift where an excluded name refers to a consultant that
    no longer exists, making the exclusion assertion vacuously true.
    """
    consultant_names = {c.name for c in scenario["consultants"]}
    for name in scenario["expected_excludes"]:
        assert name in consultant_names, (
            f"Scenario {scenario['id']!r}: expected_excludes names {name!r} "
            f"but no consultant with that name exists in the scenario."
        )


def test_no_scenario_has_both_empty_includes_and_empty_excludes() -> None:
    """Every scenario must carry at least one machine-checkable name assertion.

    A scenario with both expected_includes=[] and expected_excludes=[] has no
    testable contract — it is equivalent to no assertion at all.
    """
    vacuous = [
        s["id"] for s in ROLE_SCENARIOS if not s["expected_includes"] and not s["expected_excludes"]
    ]
    assert not vacuous, (
        f"Scenarios with no testable name assertions (both lists empty): {vacuous}. "
        "Add at least one entry to expected_includes or expected_excludes."
    )
