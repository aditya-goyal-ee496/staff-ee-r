"""Matcher pipeline behaviour: eligible consultants ranked by fit, exclusions explained."""

from __future__ import annotations

from collections.abc import Sequence

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.domain.matcher import Matcher
from staffeer.domain.models import Consultant, Role


def _matcher(consultants: Sequence[Consultant]) -> Matcher:
    return Matcher(
        supply=InMemorySupplyDemandSource(consultants=consultants),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
    )


def _remote_role() -> Role:
    return Role(
        id="R-01", title="Engineer", location="Remote-India", required_skills=("python", "sql")
    )


def test_consultant_with_fuller_skill_coverage_ranks_first() -> None:
    asha = Consultant(id="C-01", name="Asha", location="Chennai", skills=("python", "sql"))
    bina = Consultant(id="C-02", name="Bina", location="Bengaluru", skills=("python",))
    shortlist = _matcher((bina, asha)).match(_remote_role())
    assert shortlist.matches[0].consultant.name == "Asha"


def test_location_ineligible_consultant_is_excluded_with_its_reason() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", required_skills=("python",))
    pune = Consultant(id="C-01", name="Imran", location="Pune", skills=("python",))
    shortlist = _matcher((pune,)).match(role)
    assert shortlist.excluded[0].failures[0].name == "location"


def test_an_eligible_match_carries_a_skill_explanation_factor() -> None:
    asha = Consultant(id="C-01", name="Asha", location="Chennai", skills=("python", "sql"))
    shortlist = _matcher((asha,)).match(_remote_role())
    assert any(factor.source == "skills" for factor in shortlist.matches[0].explanation.factors)


def test_no_eligible_consultant_yields_no_matches() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", required_skills=("python",))
    pune = Consultant(id="C-01", name="Imran", location="Pune", skills=("python",))
    assert _matcher((pune,)).match(role).matches == ()
