"""Shared sample data for the per-port contract suites.

Each suite (`docs/rules/spec-driven-development.md` RULE-002) is parametrised over an
implementation fixture. C1 ships the null objects / in-memory source as the first
implementations; Track B–E adapters reuse these same suites unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.xlsx_supply_demand import XlsxSupplyDemandSource
from staffeer.domain.models import Consultant, Priority, Role, SupplyState
from staffeer.ports.supply_demand import SupplyDemandSource

SAMPLE_ROLE = Role(
    id="ROLE-01",
    title="Backend Engineer",
    location="Chennai",
    required_skills=("python",),
    start_date=date(2026, 7, 1),
    priority=Priority.HIGH,
)
BEACH_CONSULTANT = Consultant(
    id="beach-1",
    name="Asha Rao",
    location="Chennai",
    skills=("python",),
    state=SupplyState.BEACH,
    available_from=date(2026, 6, 1),
)


@pytest.fixture
def sample_role() -> Role:
    """The single open role the supply-demand suite expects to find."""
    return SAMPLE_ROLE


@pytest.fixture
def beach_consultant() -> Consultant:
    """The single beach consultant the supply-demand suite expects to find."""
    return BEACH_CONSULTANT


@pytest.fixture(params=["in_memory", "xlsx"])
def supply_source(
    request: pytest.FixtureRequest, workbook_factory: Callable[..., Path]
) -> SupplyDemandSource:
    """Each `SupplyDemandSource` implementation runs the same contract (RULE-002).

    Both the in-memory source and the real xlsx adapter must yield exactly `SAMPLE_ROLE` and
    `BEACH_CONSULTANT`, so the workbook rows are crafted to parse into those value objects.
    """
    if request.param == "in_memory":
        return InMemorySupplyDemandSource(roles=[SAMPLE_ROLE], consultants=[BEACH_CONSULTANT])
    path = workbook_factory(
        as_of="2026-06-01",
        roles=[
            [
                "ROLE-01",
                "Backend Engineer",
                "",
                "",
                "python",
                "2026-07-01",
                "Chennai",
                "No",
                "High",
                "",
            ]
        ],
        beach=[[1, "Asha Rao", "asha.rao@x.example", "", "python", "Chennai", "No", 10, ""]],
    )
    return XlsxSupplyDemandSource(path)
