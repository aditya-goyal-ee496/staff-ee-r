"""Contract suite for the `SemanticIndex` port (spec: docs/tasks/00b-contracts.md, C2-02).

Seven one-assertion tests verifying the structural invariants that every SemanticIndex
implementation must satisfy.  Exercised against NullSemanticIndex (always) and
MilvusSemanticIndex (when sentence_transformers + pymilvus are installed).

AAA layout — Arrange / Act / Assert — one assertion per test.
"""

from __future__ import annotations

import pytest

from staffeer.adapters.null_semantic_index import NullSemanticIndex
from staffeer.ports.semantic_index import (
    IndexItem,
    SemanticIndex,
)


def _make_null() -> SemanticIndex:
    return NullSemanticIndex()


def _make_milvus(tmp_path_factory: pytest.TempPathFactory) -> SemanticIndex:
    pytest.importorskip("sentence_transformers")
    pytest.importorskip("pymilvus")
    from staffeer.adapters.milvus_index import MilvusSemanticIndex  # noqa: PLC0415

    db_path = str(tmp_path_factory.mktemp("milvus_contract") / "contract.db")
    return MilvusSemanticIndex(db_path=db_path)


@pytest.fixture(
    params=["null", "milvus"],
    ids=["null", "milvus"],
)
def index(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> SemanticIndex:
    if request.param == "null":
        return _make_null()
    return _make_milvus(tmp_path_factory)


# T1 — implementation satisfies the SemanticIndex protocol
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
