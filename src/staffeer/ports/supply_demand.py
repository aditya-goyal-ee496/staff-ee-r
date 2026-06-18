"""`SupplyDemandSource` port — reads open roles and available consultants.

The spec (`docs/tasks/00b-contracts.md`): `role(id)` raises `SupplyDemandError` when the id is
unknown; `consultants(*states)` filters by supply state (no states → all). Implementations
exchange domain value objects only, never infrastructure types.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from staffeer.domain.models import Consultant, Role, SupplyState


@runtime_checkable
class SupplyDemandSource(Protocol):
    """Reads demand (open roles) and supply (consultants by state)."""

    def open_roles(self) -> tuple[Role, ...]:
        """All open roles. Empty when there are none — never `None`."""
        ...

    def role(self, role_id: str) -> Role:
        """The role with `role_id`, or raise `SupplyDemandError` if it does not exist."""
        ...

    def consultants(self, *states: SupplyState) -> tuple[Consultant, ...]:
        """Consultants in any of `states` (all consultants when `states` is empty)."""
        ...
