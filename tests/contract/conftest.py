"""Shared sample data for the per-port contract suites.

Each suite (`docs/rules/spec-driven-development.md` RULE-002) is parametrised over an
implementation fixture. C1 ships the null objects / in-memory source as the first
implementations; Track B–E adapters reuse these same suites unchanged.
"""

from __future__ import annotations

from datetime import date

import pytest

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.domain.models import Consultant, Priority, Role, SupplyState

SAMPLE_ROLE = Role(
    id="ROLE-01",
    title="Backend Engineer",
    location="Chennai",
    required_skills=("python",),
    start_date=date(2026, 7, 1),
    priority=Priority.HIGH,
)
BEACH_CONSULTANT = Consultant(
    id="C-01",
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


@pytest.fixture
def supply_source() -> InMemorySupplyDemandSource:
    """An in-memory `SupplyDemandSource` seeded with one role and one beach consultant."""
    return InMemorySupplyDemandSource(roles=[SAMPLE_ROLE], consultants=[BEACH_CONSULTANT])
