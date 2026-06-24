"""Null-object adapter for the `SemanticIndex` port.

Always returns empty query results and silently discards upserts.  Used when the
semantic index is disabled or unconfigured; wired by the composition root.
"""

from __future__ import annotations

from staffeer.ports.semantic_index import Hit, IndexItem


class NullSemanticIndex:
    """No-op semantic index (null object). Always returns empty results."""

    def upsert(self, item: IndexItem) -> None:
        """No-op."""

    def query(self, text: str, namespace: str, top_k: int) -> list[Hit]:
        """Return empty list (no index to query)."""
        return []
