"""`RoleParser` port — parse a free-text role description into a structured `Role`.

Spec reference: `docs/tasks/00b-contracts.md` (C2-04).

The port decouples the domain core from any concrete NLP/LLM backend used to
extract structured role data from free text.  Every implementation must accept a
free-text string and return a `Role`; on failure it raises `ValueError` (bad input)
or `staffeer.ports.reasoner.LLMReasonerError` (transport/LLM failure).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from staffeer.domain.models import Role


@runtime_checkable
class RoleParser(Protocol):
    """Port: parse a free-text description into a structured `Role`."""

    def parse(self, free_text: str) -> Role:
        """Return a `Role` parsed from `free_text`.

        Raises:
            ValueError: when the text cannot produce a valid role title.
            LLMReasonerError: when the underlying transport/LLM call fails.
        """
        ...
