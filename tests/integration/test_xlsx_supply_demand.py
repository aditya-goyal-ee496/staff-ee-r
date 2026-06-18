"""xlsx supply/demand adapter: parsing behaviour against fixture and real workbooks.

Behaviour-focused (RULE-006): assert the domain values parsed out, and that malformed input is
reported as a domain `SupplyDemandError` — never how openpyxl reads the cells.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from staffeer.adapters.xlsx_supply_demand import XlsxSupplyDemandSource
from staffeer.domain.errors import SupplyDemandError
from staffeer.domain.models import SupplyState

_REAL_WORKBOOK = Path("planning/raw-data/demand-supply.xlsx")
_needs_real_data = pytest.mark.skipif(
    not _REAL_WORKBOOK.exists(), reason="real demand-supply workbook is not present"
)


@_needs_real_data
def test_real_workbook_loads_the_named_open_role() -> None:
    source = XlsxSupplyDemandSource(_REAL_WORKBOOK)
    assert source.role("ROLE-01").title.startswith("Senior Backend Engineer")


@_needs_real_data
def test_real_workbook_marks_a_chennai_co_located_role_as_chennai_open() -> None:
    source = XlsxSupplyDemandSource(_REAL_WORKBOOK)
    assert source.role("ROLE-02").chennai_open is True


def test_role_in_chennai_with_co_location_is_marked_chennai_open(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(
        roles=[["ROLE-1", "SRE", "", "", "Kubernetes", "2026-06-15", "Chennai", "Yes", "High", ""]]
    )
    assert XlsxSupplyDemandSource(path).role("ROLE-1").chennai_open is True


def test_beach_consultant_is_available_from_the_as_of_date(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(
        as_of="2026-06-01",
        beach=[[1, "Asha", "a@x.example", "", "python", "Chennai", "No", 5, ""]],
    )
    consultant = XlsxSupplyDemandSource(path).consultants(SupplyState.BEACH)[0]
    assert consultant.available_from == date(2026, 6, 1)


def test_new_joiner_skills_are_recorded_as_unverified(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(
        joiners=[
            [1, "Vikram", "v@x.example", "Senior", "Kotlin", "2026-06-25", "Bengaluru", "Yes", ""]
        ]
    )
    consultant = XlsxSupplyDemandSource(path).consultants(SupplyState.NEW_JOINER)[0]
    assert consultant.skills_verified is False


def test_rolling_off_confidence_text_maps_to_a_weight(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(
        rolling=[
            [
                1,
                "Aarav",
                "a@x.example",
                "Lead",
                "Kotlin",
                "Meridian",
                "2026-08-18",
                "high",
                "Bengaluru",
                "No",
                "",
            ]
        ]
    )
    consultant = XlsxSupplyDemandSource(path).consultants(SupplyState.ROLLING_OFF)[0]
    assert consultant.confidence == 0.9


def test_malformed_start_date_is_reported_as_a_supply_demand_error(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(
        roles=[["ROLE-1", "SRE", "", "", "Kubernetes", "not-a-date", "Chennai", "No", "High", ""]]
    )
    with pytest.raises(SupplyDemandError):
        XlsxSupplyDemandSource(path)


def test_invalid_priority_is_reported_as_a_supply_demand_error(
    workbook_factory: Callable[..., Path],
) -> None:
    path = workbook_factory(
        roles=[["ROLE-1", "SRE", "", "", "Kubernetes", "2026-06-15", "Chennai", "No", "Urgent", ""]]
    )
    with pytest.raises(SupplyDemandError):
        XlsxSupplyDemandSource(path)
