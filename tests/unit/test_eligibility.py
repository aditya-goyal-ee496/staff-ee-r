"""Eligibility behaviour: who clears location and availability, why exclusions happen, ordering.

Tests assert observable behaviour — eligibility outcomes and the reasons surfaced to a staffing
manager — not how the constraint is computed (RULE-006).
"""

from __future__ import annotations

from datetime import date

from staffeer.domain.eligibility import (
    availability_constraint,
    location_constraint,
    screen_consultants,
)
from staffeer.domain.models import Consultant, Role


def _consultant(location: str, available_from: date | None = None) -> Consultant:
    return Consultant(id="C-01", name="Asha Rao", location=location, available_from=available_from)


def test_chennai_open_role_admits_a_chennai_consultant() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", chennai_open=True)
    assert location_constraint(_consultant("Chennai, India"), role).passed is True


def test_chennai_open_role_excludes_a_non_chennai_consultant() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", chennai_open=True)
    assert location_constraint(_consultant("Bangalore"), role).passed is False


def test_co_located_non_chennai_role_admits_a_same_city_consultant() -> None:
    role = Role(id="R-01", title="Engineer", location="Pune", co_location=True)
    assert location_constraint(_consultant("Pune, India"), role).passed is True


def test_co_located_non_chennai_role_excludes_another_city() -> None:
    role = Role(id="R-01", title="Engineer", location="Pune", co_location=True)
    assert location_constraint(_consultant("Bangalore"), role).passed is False


def test_remote_india_role_admits_any_india_location() -> None:
    role = Role(id="R-01", title="Engineer", location="Remote - India")
    assert location_constraint(_consultant("Bangalore"), role).passed is True


def test_remote_india_role_excludes_a_non_india_location() -> None:
    role = Role(id="R-01", title="Engineer", location="Remote - India")
    assert location_constraint(_consultant("London, UK"), role).passed is False


def test_on_site_role_admits_a_same_city_consultant() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai")
    assert location_constraint(_consultant("Chennai"), role).passed is True


def test_on_site_role_excludes_another_city() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai")
    assert location_constraint(_consultant("Pune"), role).passed is False


def test_excluded_consultant_is_told_where_the_role_needs_them() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai")
    assert "Pune" in location_constraint(_consultant("Pune"), role).reason


def test_beach_consultant_with_no_end_date_is_available_for_a_future_start() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", start_date=date(2026, 7, 1))
    assert availability_constraint(_consultant("Chennai"), role).passed is True


def test_consultant_free_within_the_buffer_is_available() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", start_date=date(2026, 7, 1))
    rolling_off = _consultant("Chennai", available_from=date(2026, 7, 5))
    assert availability_constraint(rolling_off, role, buffer_days=7).passed is True


def test_consultant_free_only_beyond_the_buffer_is_unavailable() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", start_date=date(2026, 7, 1))
    rolling_off = _consultant("Chennai", available_from=date(2026, 8, 1))
    assert availability_constraint(rolling_off, role, buffer_days=7).passed is False


def test_screening_lists_eligible_consultants_before_excluded_ones() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai")
    shortlist = screen_consultants((_consultant("Pune"), _consultant("Chennai")), role)
    assert (shortlist[0].eligible, shortlist[1].eligible) == (True, False)


def test_screening_excludes_everyone_when_no_consultant_fits_the_role() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai")
    shortlist = screen_consultants((_consultant("Pune"), _consultant("Bangalore")), role)
    assert [result.eligible for result in shortlist] == [False, False]
