"""Contract suite for the `SemanticIndex` port (spec: docs/tasks/00b-contracts.md, C2-02).

Seven one-assertion tests verifying the structural invariants that every SemanticIndex
implementation must satisfy.  Exercised against NullSemanticIndex so the suite runs with
no network I/O.  Tests that touch real Milvus belong in tests/integration/.

AAA layout — Arrange / Act / Assert — one assertion per test.
"""

from __future__ import annotations

import pytest

from staffeer.ports.semantic_index import (
    IndexItem,
    NullSemanticIndex,
    SemanticIndex,
)


@pytest.fixture
def index() -> SemanticIndex:
    return NullSemanticIndex()


# T1 — NullSemanticIndex satisfies the SemanticIndex protocol
def test_implementation_satisfies_the_protocol(index: SemanticIndex) -> None:
    assert isinstance(index, SemanticIndex)


# T2 — query on empty index returns empty list
def test_query_on_empty_index_returns_empty_list(index: SemanticIndex) -> None:
    # Arrange / Act
    result = index.query("python", "skills", 3)
    # Assert
    assert result == []


# T3 — query with k=0 returns empty list (boundary: zero results requested)
def test_query_with_k_0_returns_empty_list(index: SemanticIndex) -> None:
    # Arrange / Act
    result = index.query("python", "skills", 0)
    # Assert
    assert result == []


# T4 — upsert returns None (void contract)
def test_upsert_returns_none(index: SemanticIndex) -> None:
    # Arrange
    item = IndexItem(id="C-01", text="python django", namespace="skills")
    # Act
    result = index.upsert(item)
    # Assert
    assert result is None


# T5 — upsert duplicate id is idempotent: subsequent query still returns a list
def test_upsert_duplicate_id_is_idempotent(index: SemanticIndex) -> None:
    # Arrange
    item = IndexItem(id="C-01", text="python django", namespace="skills")
    index.upsert(item)
    # Act
    index.upsert(item)
    result = index.query("python", "skills", 5)
    # Assert
    assert isinstance(result, list)


# T6 — upsert with empty text returns None (empty-text edge case)
def test_upsert_empty_text_returns_none(index: SemanticIndex) -> None:
    # Arrange
    item = IndexItem(id="C-02", text="", namespace="skills")
    # Act
    result = index.upsert(item)
    # Assert
    assert result is None


# T7 — query with empty namespace returns a list (empty-namespace edge case)
def test_query_with_empty_namespace_returns_list(index: SemanticIndex) -> None:
    # Arrange / Act
    result = index.query("python", "", 3)
    # Assert
    assert isinstance(result, list)
