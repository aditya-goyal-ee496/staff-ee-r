"""Composition root — the single place adapters are wired to ports.

`build_matcher(config)` picks a real-vs-null implementation per port from `StaffeerConfig` and
assembles the `Matcher`. Tracks add real adapters here (one null→real swap per integration
slice); the CLI never wires adapters itself (`docs/tasks/parallelization-guide.md`). In C1 every
port defaults to its null object, so the matcher runs end-to-end and returns an empty shortlist.
"""

from __future__ import annotations

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.config import StaffeerConfig
from staffeer.domain.errors import StaffeerError
from staffeer.domain.matcher import Matcher
from staffeer.ports.pii import PIIScrubber


def build_matcher(config: StaffeerConfig) -> Matcher:
    """Assemble a `Matcher` from `config`, defaulting every port to its null object.

    Fails closed: a wired LLM or semantic path with no real `PIIScrubber` raises, so
    unscrubbed text can never reach an LLM (`docs/rules/security.md`).
    """
    pii = _build_pii_scrubber(config)
    if (config.llm_enabled or config.semantic_enabled) and isinstance(pii, NullPIIScrubber):
        raise StaffeerError(
            "LLM/semantic path requires a real PIIScrubber; refusing to wire a null scrubber "
            "(fail closed)"
        )
    return Matcher(
        supply=InMemorySupplyDemandSource(),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=pii,
        include_states=config.include_states,
        weights=config.weights,
    )


def _build_pii_scrubber(config: StaffeerConfig) -> PIIScrubber:
    """Select the PII scrubber. Only the null object exists until Track C wires Presidio."""
    return NullPIIScrubber()
