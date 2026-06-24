"""Deterministic hard-constraint golden table — must be 100% green (ADR-001).

Each scenario fixes a role and a beach supply pool, then asserts the exact ranked shortlist and
the exact set of explained exclusions. Covers the four location cases, the availability buffer,
deterministic skill ranking, and the mandatory no-viable-match negative scenario.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

import pytest

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import Consultant, Role


@dataclass(frozen=True)
class _Scenario:
    name: str
    role: Role
    consultants: Sequence[Consultant]
    ranked: list[str]
    excluded: set[str] = field(default_factory=set)


def _beach(
    name: str,
    location: str,
    skills: tuple[str, ...],
    *,
    chennai_open: bool = False,
    available_from: date | None = None,
) -> Consultant:
    return Consultant(
        id=name.lower(),
        name=name,
        location=location,
        skills=skills,
        chennai_open=chennai_open,
        available_from=available_from,
    )


_SCENARIOS = (
    _Scenario(
        name="chennai_co_located_admits_chennai_based_or_chennai_open",
        role=Role(
            id="R-SRE",
            title="SRE",
            location="Chennai",
            required_skills=("kubernetes",),
            co_location=True,
            chennai_open=True,
        ),
        consultants=(
            _beach("Aarav", "Bengaluru", ("kubernetes",)),  # not Chennai-open -> excluded
            _beach("Karan", "Bengaluru", ("kubernetes",), chennai_open=True),
            _beach("Karthik", "Chennai", ("kubernetes",)),
        ),
        ranked=["Karan", "Karthik"],  # tie on coverage -> name tie-break
        excluded={"Aarav"},
    ),
    _Scenario(
        name="remote_india_ranks_by_skill_coverage",
        role=Role(
            id="R-ML",
            title="ML Engineer",
            location="Remote-India",
            required_skills=("python", "sql"),
        ),
        consultants=(
            _beach("Bina", "Bengaluru", ("python",)),
            _beach("Asha", "Chennai", ("python", "sql")),
            _beach("Chetan", "Delhi NCR", ("java",)),
        ),
        ranked=["Asha", "Bina", "Chetan"],
        excluded=set(),
    ),
    _Scenario(
        name="on_site_chennai_with_no_local_consultant_yields_no_match",
        role=Role(id="R-QA", title="QA", location="Chennai", required_skills=("python",)),
        consultants=(
            _beach("Imran", "Pune", ("python",)),
            _beach("Bina", "Bengaluru", ("python",)),
        ),
        ranked=[],
        excluded={"Imran", "Bina"},
    ),
    _Scenario(
        name="availability_beyond_the_buffer_is_excluded",
        role=Role(
            id="R-API",
            title="Backend",
            location="Remote-India",
            required_skills=("python",),
            start_date=date(2026, 7, 1),
        ),
        consultants=(
            _beach("Asha", "Chennai", ("python",)),  # available now
            _beach("Late", "Pune", ("python",), available_from=date(2026, 8, 1)),
        ),
        ranked=["Asha"],
        excluded={"Late"},
    ),
    # Skill-ranking scenario: full match > partial+adjacent > adjacent-only.
    # java↔kotlin adjacency is verified from DEFAULT_ADJACENCY["kotlin"] == ("java",).
    _Scenario(
        name="skill_ranking_orders_by_coverage",
        role=Role(
            id="R-SKL",
            title="Backend Engineer",
            location="Remote-India",
            required_skills=("python", "sql", "kotlin"),
        ),
        consultants=(
            _beach("Deepa", "Chennai", ("python", "sql", "kotlin")),  # full match: score 1.0
            _beach("Elan", "Pune", ("python", "java")),  # python exact + java→kotlin adjacent
            _beach("Farhan", "Bengaluru", ("java",)),  # java→kotlin adjacent only
        ),
        ranked=["Deepa", "Elan", "Farhan"],
        excluded=set(),
    ),
    # Negative scenario: no consultant covers the required skills; system still returns a ranked
    # list with explicit gap explanations — never silently drops or fabricates a match.
    _Scenario(
        name="no_full_match_still_returns_ranked_list_with_gap_explanations",
        role=Role(
            id="R-GAP",
            title="Systems Engineer",
            location="Remote-India",
            required_skills=("rust", "wasm"),
        ),
        consultants=(
            _beach("Gita", "Chennai", ("python",)),  # no rust/wasm adjacency -> score 0.0
            _beach("Hari", "Bengaluru", ("java",)),  # no rust/wasm adjacency -> score 0.0
        ),
        # Both score 0.0; name tie-break: G < H.
        ranked=["Gita", "Hari"],
        excluded=set(),
    ),
)


def _matcher(consultants: Sequence[Consultant]) -> Matcher:
    return Matcher(
        supply=InMemorySupplyDemandSource(consultants=consultants),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
    )


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=lambda scenario: scenario.name)
def test_ranked_shortlist_matches_the_golden_expectation(scenario: _Scenario) -> None:
    shortlist = _matcher(scenario.consultants).match(scenario.role)
    assert [match.consultant.name for match in shortlist.matches] == scenario.ranked


@pytest.mark.parametrize("scenario", _SCENARIOS, ids=lambda scenario: scenario.name)
def test_exclusions_match_the_golden_expectation(scenario: _Scenario) -> None:
    shortlist = _matcher(scenario.consultants).match(scenario.role)
    assert {result.consultant.name for result in shortlist.excluded} == scenario.excluded


_GAP_SCENARIO = next(
    (
        s
        for s in _SCENARIOS
        if s.name == "no_full_match_still_returns_ranked_list_with_gap_explanations"
    ),
    None,
)
_GAP_SCENARIO_NAME = "no_full_match_still_returns_ranked_list_with_gap_explanations"
assert _GAP_SCENARIO is not None, f"Scenario {_GAP_SCENARIO_NAME!r} not found in _SCENARIOS"

_GAP_NAMES = [c.name for c in _GAP_SCENARIO.consultants]


def test_gap_scenario_ranked_list_is_non_empty() -> None:
    """The gap scenario must produce a non-empty ranked list — no consultant is silently dropped."""
    shortlist = _matcher(_GAP_SCENARIO.consultants).match(_GAP_SCENARIO.role)  # type: ignore[union-attr]
    assert len(shortlist.matches) > 0


@pytest.mark.parametrize("consultant_name", _GAP_NAMES)
def test_gap_scenario_ranked_match_has_skills_factor(consultant_name: str) -> None:
    """Each ranked match in the gap scenario must carry at least one skills explanation factor."""
    shortlist = _matcher(_GAP_SCENARIO.consultants).match(_GAP_SCENARIO.role)  # type: ignore[union-attr]
    match = next(m for m in shortlist.matches if m.consultant.name == consultant_name)
    skill_factors = [f for f in match.explanation.factors if f.source == "skills"]
    assert skill_factors, f"{consultant_name} has no skills factor"


@pytest.mark.parametrize("consultant_name", _GAP_NAMES)
def test_gap_scenario_ranked_match_skills_factor_has_detail(consultant_name: str) -> None:
    """Each skills explanation factor in the gap scenario must carry non-empty detail text."""
    shortlist = _matcher(_GAP_SCENARIO.consultants).match(_GAP_SCENARIO.role)  # type: ignore[union-attr]
    match = next(m for m in shortlist.matches if m.consultant.name == consultant_name)
    skill_factors = [f for f in match.explanation.factors if f.source == "skills"]
    assert skill_factors[0].detail, f"{consultant_name} skills factor detail is empty"
