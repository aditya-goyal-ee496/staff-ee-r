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
from staffeer.domain.models import Consultant, Role, SupplyState


def _consultant(location: str, available_from: date | None = None) -> Consultant:
    return Consultant(id="C-01", name="Asha Rao", location=location, available_from=available_from)


def test_chennai_open_role_admits_a_chennai_consultant() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", chennai_open=True)
    assert location_constraint(_consultant("Chennai, India"), role).passed is True


def test_chennai_open_role_admits_a_chennai_open_consultant_based_elsewhere() -> None:
    role = Role(id="R-01", title="Engineer", location="Chennai", chennai_open=True)
    willing = Consultant(id="C-01", name="Karan", location="Bengaluru", chennai_open=True)
    assert location_constraint(willing, role).passed is True


def test_chennai_open_role_excludes_an_unwilling_non_chennai_consultant() -> None:
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


# ---------------------------------------------------------------------------
# 08-01: Roll-off buffer-boundary eligibility tests
# ---------------------------------------------------------------------------


def test_roll_off_available_within_buffer_is_eligible() -> None:
    # Arrange
    role = Role(id="R-01", title="Engineer", location="Remote-India", start_date=date(2026, 7, 1))
    consultant = Consultant(
        id="C-RO",
        name="Rolling Rao",
        location="Chennai",
        state=SupplyState.ROLLING_OFF,
        available_from=date(2026, 7, 4),  # start_date + 3 days
    )
    # Act
    result = availability_constraint(consultant, role, buffer_days=7)
    # Assert
    assert result.passed is True


def test_roll_off_available_after_buffer_is_excluded() -> None:
    # Arrange
    role = Role(id="R-01", title="Engineer", location="Remote-India", start_date=date(2026, 7, 1))
    consultant = Consultant(
        id="C-RO",
        name="Late Rao",
        location="Chennai",
        state=SupplyState.ROLLING_OFF,
        available_from=date(2026, 7, 15),  # start_date + 14 days, beyond 7-day buffer
    )
    # Act
    result = availability_constraint(consultant, role, buffer_days=7)
    # Assert
    assert result.passed is False


def test_late_roll_off_exclusion_reason_names_the_dates() -> None:
    # Arrange
    role = Role(id="R-01", title="Engineer", location="Remote-India", start_date=date(2026, 7, 1))
    consultant = Consultant(
        id="C-RO",
        name="Late Rao",
        location="Chennai",
        state=SupplyState.ROLLING_OFF,
        available_from=date(2026, 7, 15),
    )
    # Act
    result = availability_constraint(consultant, role, buffer_days=7)
    # Assert
    assert "2026-07-15" in result.reason and "2026-07-01" in result.reason


# ---------------------------------------------------------------------------
# 08-11: Late-roll-off no-match NEGATIVE scenario
# ---------------------------------------------------------------------------


def test_late_roll_off_produces_no_eligible_results() -> None:
    # Arrange
    role = Role(id="R-01", title="Engineer", location="Remote-India", start_date=date(2026, 7, 1))
    consultant = Consultant(
        id="C-RO",
        name="Way Late Rao",
        location="Chennai",
        state=SupplyState.ROLLING_OFF,
        available_from=date(2026, 9, 1),  # far beyond any buffer
    )
    # Act
    results = screen_consultants((consultant,), role, buffer_days=7)
    # Assert
    assert not any(result.eligible for result in results)
