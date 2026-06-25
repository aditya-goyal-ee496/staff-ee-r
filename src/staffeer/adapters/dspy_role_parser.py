"""`RoleParser` adapter — DSPy free-text role parsing via OpenRouter.

Implements the `RoleParser` port by delegating to `parse_free_text_role` in the
DSPy/OpenRouter adapter.  PII is scrubbed before any text reaches the LLM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from staffeer.domain.models import Role
    from staffeer.ports.pii import PIIScrubber


class DspyRoleParser:
    """Parse a free-text role description into a `Role` via DSPy + OpenRouter."""

    def __init__(
        self,
        *,
        api_key: str,
        pii_scrubber: PIIScrubber,
        model: str = "openai/gpt-4o-mini",
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required and cannot be empty")
        self._api_key = api_key
        self._pii_scrubber = pii_scrubber
        self._model = model

    def parse(self, free_text: str) -> Role:
        """Return a `Role` parsed from `free_text`; PII is scrubbed before LLM call."""
        from staffeer.adapters.dspy_openrouter import parse_free_text_role  # noqa: PLC0415

        return parse_free_text_role(
            free_text,
            api_key=self._api_key,
            model=self._model,
            pii_scrubber=self._pii_scrubber,
        )
