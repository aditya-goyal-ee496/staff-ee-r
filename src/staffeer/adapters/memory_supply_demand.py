"""In-memory `SupplyDemandSource` — the default (empty) source and a test double.

`build_matcher` defaults to an empty instance until the xlsx adapter is wired (I1). Seeded
with roles/consultants, it is also the implementation the supply-demand contract suite runs
against, so the real xlsx adapter inherits the same proven behaviour.
"""

from __future__ import annotations

from collections.abc import Iterable

from staffeer.domain.errors import SupplyDemandError
from staffeer.domain.models import Consultant, Role, SupplyState


class InMemorySupplyDemandSource:
    """Serves roles and consultants held in memory."""

    def __init__(
        self,
        roles: Iterable[Role] = (),
        consultants: Iterable[Consultant] = (),
    ) -> None:
        self._roles = tuple(roles)
        self._consultants = tuple(consultants)

    def open_roles(self) -> tuple[Role, ...]:
        """All seeded roles (empty when none were provided)."""
        return self._roles

    def role(self, role_id: str) -> Role:
        """The role with `role_id`, or raise `SupplyDemandError` if unknown."""
        for role in self._roles:
            if role.id == role_id:
                return role
        raise SupplyDemandError(f"role not found: {role_id}")

    def consultants(self, *states: SupplyState) -> tuple[Consultant, ...]:
        """Consultants filtered by `states` (all when no states are given)."""
        if not states:
            return self._consultants
        return tuple(c for c in self._consultants if c.state in states)
