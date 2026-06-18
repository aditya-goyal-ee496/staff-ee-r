"""Contract suite for the `SupplyDemandSource` port (spec: `docs/tasks/00b-contracts.md`)."""

from __future__ import annotations

import pytest

from staffeer.domain.errors import SupplyDemandError
from staffeer.domain.models import Consultant, Role, SupplyState
from staffeer.ports.supply_demand import SupplyDemandSource


def test_implementation_satisfies_the_port(supply_source: SupplyDemandSource) -> None:
    assert isinstance(supply_source, SupplyDemandSource)


def test_open_roles_returns_the_seeded_roles(
    supply_source: SupplyDemandSource, sample_role: Role
) -> None:
    assert supply_source.open_roles() == (sample_role,)


def test_role_returns_the_role_with_the_given_id(
    supply_source: SupplyDemandSource, sample_role: Role
) -> None:
    assert supply_source.role(sample_role.id) == sample_role


def test_unknown_role_id_raises_supply_demand_error(supply_source: SupplyDemandSource) -> None:
    with pytest.raises(SupplyDemandError):
        supply_source.role("ROLE-404")


def test_consultants_filters_by_requested_state(
    supply_source: SupplyDemandSource, beach_consultant: Consultant
) -> None:
    assert supply_source.consultants(SupplyState.BEACH) == (beach_consultant,)


def test_consultants_excludes_unrequested_states(supply_source: SupplyDemandSource) -> None:
    assert supply_source.consultants(SupplyState.ROLLING_OFF) == ()
