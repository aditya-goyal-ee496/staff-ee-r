"""Semantic index port — vector storage and similarity search over scrubbed content.

Spec: docs/tasks/00b-contracts.md (C2, SemanticIndex).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from staffeer.domain.models import ValueObject


class IndexItem(ValueObject):
    """One unit of content to index (a scrubbed skill summary or profile excerpt)."""

    id: str
    text: str
    namespace: str
    metadata: dict[str, str] = {}


class Hit(ValueObject):
    """One result returned by a semantic query."""

    id: str
    score: float
    text: str
    metadata: dict[str, str] = {}


@runtime_checkable
class SemanticIndex(Protocol):
    """Persistent vector index; upsert(item), query(text, namespace, top_k) -> [Hit]."""

    def upsert(self, item: IndexItem) -> None:
        """Persist or update `item`; idempotent on `id`."""
        ...

    def query(self, text: str, namespace: str, top_k: int) -> list[Hit]:
        """Return up to `top_k` nearest neighbours for `text`; empty list when index is empty."""
        ...


class NullSemanticIndex:
    """No-op semantic index (null object). Always returns empty results."""

    def upsert(self, item: IndexItem) -> None:
        """No-op."""
        pass

    def query(self, text: str, namespace: str, top_k: int) -> list[Hit]:
        """Return empty list (no index to query)."""
        return []
