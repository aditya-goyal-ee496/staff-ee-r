"""Null-object adapter for the `RoleParser` port.

Always raises `ValueError` — there is no LLM to parse free text when this adapter
is active.  The composition root wires this when `llm_enabled` is False or no
API key is configured, so the CLI can surface a clear error.
"""

from __future__ import annotations

from staffeer.domain.models import Role


class NullRoleParser:
    """Null-object implementation — always raises; free-text parsing requires an LLM."""

    def parse(self, free_text: str) -> Role:
        raise ValueError("free-text role parsing requires OPENROUTER_API_KEY and llm_enabled=True")
