"""`Matcher` — the application service that runs the matching pipeline over the ports.

It depends only on port abstractions and domain models (never on adapters or config), so it
stays pure and testable. In C1 the pipeline is inert: `match` returns an empty `Shortlist`.
Tracks A–E fill the stages (filter → score → rank → explain) behind this frozen signature.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from staffeer.domain.models import Role, Shortlist, SupplyState
from staffeer.ports.feedback import FeedbackStore
from staffeer.ports.pii import PIIScrubber
from staffeer.ports.profiles import ProfileParser
from staffeer.ports.supply_demand import SupplyDemandSource


@dataclass(frozen=True)
class Matcher:
    """Orchestrates ingest → scrub → filter → score → rank → explain for one role."""

    supply: SupplyDemandSource
    profiles: ProfileParser
    feedback: FeedbackStore
    pii: PIIScrubber
    include_states: tuple[SupplyState, ...] = (SupplyState.BEACH,)
    weights: Mapping[str, float] = field(default_factory=dict)

    def match(self, role: Role) -> Shortlist:
        """Return the ranked, explained shortlist for `role`.

        Inert in C1 — an empty shortlist. Each track appends a pipeline stage behind this
        signature without reshaping it (`docs/tasks/00b-contracts.md`).
        """
        return Shortlist(role=role)
