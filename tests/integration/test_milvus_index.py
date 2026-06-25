"""Integration tests for MilvusSemanticIndex — round-trip and semantic retrieval (slice 05).

Marked `integration`; skipped when sentence_transformers or pymilvus are not installed.
Each test is independently arranged with a fresh index (via the `milvus_index` fixture) so
tests do not share state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("sentence_transformers")
pytest.importorskip("pymilvus")

from staffeer.adapters.milvus_index import MilvusSemanticIndex  # noqa: E402
from staffeer.ports.semantic_index import IndexItem  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture
def milvus_index(tmp_path: Path) -> MilvusSemanticIndex:
    """A fresh MilvusSemanticIndex backed by a temp file for each test."""
    db_path = str(tmp_path / "test.db")
    return MilvusSemanticIndex(db_path=db_path)


# ---------------------------------------------------------------------------
# 05-15 — round-trip: upsert then query returns the indexed item
# ---------------------------------------------------------------------------


def test_upsert_then_query_returns_hit_for_indexed_item(milvus_index: MilvusSemanticIndex) -> None:
    """Upsert one item then query with a closely related phrase; assert the item is returned."""
    # Arrange
    milvus_index.upsert(
        IndexItem(id="C-01", text="python django web development", namespace="skills")
    )
    # Act
    hits = milvus_index.query("python web", namespace="skills", top_k=1)
    # Assert
    assert hits[0].id == "C-01"


# ---------------------------------------------------------------------------
# 05-16 — semantic (not lexical) retrieval: JVM-backend query finds Java consultant
# ---------------------------------------------------------------------------


def test_semantically_related_but_lexically_different_skill_is_retrieved(
    milvus_index: MilvusSemanticIndex,
) -> None:
    """Semantic similarity bridges the lexical gap between query and indexed text."""
    # Arrange
    milvus_index.upsert(
        IndexItem(id="C-java", text="backend Java Spring microservices", namespace="skills")
    )
    milvus_index.upsert(IndexItem(id="C-css", text="frontend CSS design", namespace="skills"))
    # Act
    hits = milvus_index.query("JVM enterprise backend", namespace="skills", top_k=1)
    # Assert
    assert hits[0].id == "C-java"


# ---------------------------------------------------------------------------
# 05-17 — NEGATIVE: empty index returns empty list (no hallucination)
# ---------------------------------------------------------------------------


def test_query_with_no_relevant_match_returns_empty_list(tmp_path: Path) -> None:
    """NEGATIVE: a freshly created empty index must return [] for any query."""
    # Arrange — fresh index with nothing upserted
    empty_index = MilvusSemanticIndex(db_path=str(tmp_path / "empty.db"))
    # Act
    result = empty_index.query("python backend engineer", namespace="skills", top_k=3)
    # Assert
    assert result == []
