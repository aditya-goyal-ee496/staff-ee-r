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
