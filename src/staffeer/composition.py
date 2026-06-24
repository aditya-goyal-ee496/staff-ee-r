"""Composition root — the single place adapters are wired to ports.

`build_matcher(config)` picks a real-vs-null implementation per port from `StaffeerConfig` and
assembles the `Matcher`. Tracks add real adapters here (one null→real swap per integration
slice); the CLI never wires adapters itself (`docs/tasks/parallelization-guide.md`). In C1 every
port defaults to its null object, so the matcher runs end-to-end and returns an empty shortlist.
"""

from __future__ import annotations

from pathlib import Path

try:
    import structlog

    _log = structlog.get_logger(__name__)
except ImportError:  # pragma: no cover
    import logging

    _log = logging.getLogger(__name__)

from staffeer.adapters.docling_profiles import DoclingProfileParser
from staffeer.adapters.dspy_role_parser import DspyRoleParser
from staffeer.adapters.markdown_feedback import MarkdownFeedbackStore
from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource
from staffeer.adapters.null_feedback import NullFeedbackStore
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner
from staffeer.adapters.null_pii import NullPIIScrubber
from staffeer.adapters.null_profiles import NullProfileParser
from staffeer.adapters.null_role_parser import NullRoleParser
from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.adapters.presidio_pii import PresidioPIIScrubber
from staffeer.adapters.xlsx_supply_demand import XlsxSupplyDemandSource
from staffeer.config import StaffeerConfig
from staffeer.domain.errors import StaffeerError
from staffeer.domain.matcher import Matcher
from staffeer.ports.feedback import FeedbackStore
from staffeer.ports.pii import PIIScrubber
from staffeer.ports.profiles import ProfileParser
from staffeer.ports.reasoner import LLMReasoner
from staffeer.ports.role_parser import RoleParser
from staffeer.ports.semantic_index import SemanticIndex
from staffeer.ports.supply_demand import SupplyDemandSource


def build_matcher(config: StaffeerConfig) -> Matcher:
    """Assemble a `Matcher` from `config`, defaulting every port to its null object.

    Fails closed: a wired LLM or semantic path with no real `PIIScrubber` raises, so
    unscrubbed text can never reach an LLM (`.claude/principles/security.md`).
    """
    pii = _build_pii_scrubber(config)
    if (config.llm_enabled or config.semantic_enabled) and isinstance(pii, NullPIIScrubber):
        raise StaffeerError(
            "LLM/semantic path requires a real PIIScrubber; refusing to wire a null scrubber "
            "(fail closed)"
        )
    return Matcher(
        supply=_build_supply(config),
        profiles=_build_profiles(config),
        feedback=_build_feedback(config),
        pii=pii,
        include_states=config.include_states,
        weights=config.weights,
        semantic_index=_build_semantic_index(config),
        reasoner=_build_reasoner(config),
    )


def _build_supply(config: StaffeerConfig) -> SupplyDemandSource:
    """Load supply/demand from the configured workbook, or an empty in-memory source."""
    if config.data_path:
        return XlsxSupplyDemandSource(config.data_path)
    return InMemorySupplyDemandSource()


def _build_profiles(config: StaffeerConfig) -> ProfileParser:
    """Build a `ProfileParser` from config; return null when profiles disabled."""
    if config.profiles_enabled:
        return DoclingProfileParser()
    return NullProfileParser()


def _build_feedback(config: StaffeerConfig) -> FeedbackStore:
    """Build a `FeedbackStore` from config; return null when feedback disabled."""
    if config.feedback_dir:
        return MarkdownFeedbackStore(Path(config.feedback_dir))
    return NullFeedbackStore()


def _build_pii_scrubber(config: StaffeerConfig) -> PIIScrubber:
    """Select the PII scrubber: real Presidio on the LLM/semantic path, else the null object."""
    if config.llm_enabled or config.semantic_enabled:
        return PresidioPIIScrubber()
    return NullPIIScrubber()


def _build_semantic_index(config: StaffeerConfig) -> SemanticIndex:
    """Return the null semantic index; a real Milvus adapter slots in here later."""
    return NullSemanticIndex()


def build_role_parser(config: StaffeerConfig) -> RoleParser:
    """Return a `RoleParser` wired from `config`.

    Wires `DspyRoleParser` when `llm_enabled` is True and an API key is set;
    otherwise returns `NullRoleParser` (which raises on `parse`, surfacing a clear
    error to the caller).  The PII scrubber is always wired before reaching the LLM.
    """
    pii = _build_pii_scrubber(config)
    if config.llm_enabled and config.openrouter_api_key:
        return DspyRoleParser(api_key=config.openrouter_api_key, pii_scrubber=pii)
    return NullRoleParser()


def _build_reasoner(config: StaffeerConfig) -> LLMReasoner:
    """Wire the LLM reasoner: DspyOpenRouterReasoner when enabled + key set; else null.

    When llm_enabled is True but no key is configured, falls back to NullLLMReasoner so
    the composition succeeds and PII wiring can be verified.  DspyOpenRouterReasoner raises
    ValueError at construction time when api_key is falsy — it does not defer the check.
    """
    if config.llm_enabled and config.openrouter_api_key:
        # Lazy import: composition.py must remain import-clean without dspy.
        from staffeer.adapters.dspy_openrouter import DspyOpenRouterReasoner  # noqa: PLC0415

        return DspyOpenRouterReasoner(api_key=config.openrouter_api_key)
    if config.llm_enabled and not config.openrouter_api_key:
        _log.warning("llm_enabled_but_no_key_fallback_to_null")
    return NullLLMReasoner()
