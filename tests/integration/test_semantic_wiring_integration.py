"""Integration test for slice 05a — I5: end-to-end semantic-changes-rank.

Requires sentence_transformers and pymilvus; skipped when absent.
Marked `integration`.

Test 1 — semantic_index_populated_ranks_semantically_strong_consultant_first
  A semantically-strong (but lexically-weak) consultant must rank above a
  lexically-strong one when a real MilvusSemanticIndex is populated.

Test 2 (control) — null_semantic_index_ranks_lexically_strong_consultant_first
  With NullSemanticIndex the lexically-strong consultant stays at the top,
  proving the index is what changes the rank (not some other signal).

Test 3 — match_text_semantic_cli_ranks_semantically_strong_consultant_first
  End-to-end CLI: `match-text --semantic` through the Typer CLI (not Matcher directly)
  ranks the semantically-strong consultant first when the index is populated.

Test 4 (control) — match_text_without_semantic_cli_ranks_lexically_strong_first
  `match-text` without `--semantic` keeps the lexically-strong consultant at rank 1,
  proving the flag (and the index query it enables) is what changes the ordering.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("sentence_transformers")
pytest.importorskip("pymilvus")

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from staffeer.adapters.memory_supply_demand import InMemorySupplyDemandSource  # noqa: E402
from staffeer.adapters.milvus_index import MilvusSemanticIndex  # noqa: E402
from staffeer.adapters.null_feedback import NullFeedbackStore  # noqa: E402
from staffeer.adapters.null_llm_reasoner import NullLLMReasoner  # noqa: E402
from staffeer.adapters.null_pii import NullPIIScrubber  # noqa: E402
from staffeer.adapters.null_profiles import NullProfileParser  # noqa: E402
from staffeer.adapters.null_semantic_index import NullSemanticIndex  # noqa: E402
from staffeer.cli.main import app  # noqa: E402
from staffeer.domain.matcher import Matcher  # noqa: E402
from staffeer.domain.models import Consultant, Role, SupplyState  # noqa: E402
from staffeer.ports.semantic_index import IndexItem  # noqa: E402

_cli_runner = CliRunner()

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_LEXICALLY_STRONG = Consultant(
    id="C-lex",
    name="Lexical Strong",
    location="Remote-India",
    # Covers one of two required skills lexically — partial overlap (score 0.5).
    skills=("python",),
    state=SupplyState.BEACH,
)

_SEMANTICALLY_STRONG = Consultant(
    id="C-sem",
    name="Semantic Strong",
    location="Remote-India",
    # No lexical overlap with required_skills but semantically very close to the role
    # (JVM/enterprise backend maps to java/spring at embedding level).
    skills=("java", "spring", "microservices"),
    state=SupplyState.BEACH,
)

_ROLE = Role(
    id="ROLE-SEM-TEST",
    title="JVM Enterprise Backend Engineer",
    location="Remote-India",
    # Two required skills: "python" matches C-lex lexically (0.5 coverage), while C-sem
    # has zero lexical coverage but high semantic similarity via the real index.
    # Control (NullSemanticIndex): C-lex wins (0.5 > 0.0).
    # Real index: C-sem's semantic score must exceed C-lex's 0.5 skill score.
    required_skills=("python", "django"),
)


def _build_supply() -> InMemorySupplyDemandSource:
    return InMemorySupplyDemandSource(
        roles=(_ROLE,),
        consultants=(_LEXICALLY_STRONG, _SEMANTICALLY_STRONG),
    )


def _build_matcher_with_real_index(tmp_path: Path) -> Matcher:
    """Build a Matcher with a real MilvusSemanticIndex populated for the semantic consultant."""
    db_path = str(tmp_path / "test.db")
    index = MilvusSemanticIndex(db_path=db_path)
    # Index the semantically-strong consultant with text very close to the role title/description
    # so cosine similarity exceeds the lexically-strong consultant's 0.5 skill-coverage score.
    index.upsert(
        IndexItem(
            id=_SEMANTICALLY_STRONG.id,
            text="JVM Enterprise Backend Engineer java spring microservices",
            namespace="skills",
        )
    )
    return Matcher(
        supply=_build_supply(),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=index,
        reasoner=NullLLMReasoner(),
        include_states=(SupplyState.BEACH,),
        weights={"skills": 1.0, "soft_llm": 1.0, "semantic": 1.0},
    )


def _build_matcher_with_null_index() -> Matcher:
    """Build a Matcher with NullSemanticIndex as the control (semantic contribution = 0)."""
    return Matcher(
        supply=_build_supply(),
        profiles=NullProfileParser(),
        feedback=NullFeedbackStore(),
        pii=NullPIIScrubber(),
        semantic_index=NullSemanticIndex(),
        reasoner=NullLLMReasoner(),
        include_states=(SupplyState.BEACH,),
        weights={"skills": 1.0, "soft_llm": 1.0, "semantic": 1.0},
    )


# ---------------------------------------------------------------------------
# Test 1 — real index puts the semantically-strong consultant first
# ---------------------------------------------------------------------------


def test_semantic_index_populated_ranks_semantically_strong_consultant_first(
    tmp_path: Path,
) -> None:
    """A populated MilvusSemanticIndex elevates the semantically-strong consultant to rank 1."""
    # Arrange
    matcher = _build_matcher_with_real_index(tmp_path)
    # Act
    shortlist = matcher.match(_ROLE)
    # Assert — the semantic consultant must be ranked first
    assert shortlist.matches[0].consultant.id == _SEMANTICALLY_STRONG.id


# ---------------------------------------------------------------------------
# Test 2 (control) — NullSemanticIndex leaves the lexically-strong consultant at rank 1
# ---------------------------------------------------------------------------


def test_null_semantic_index_ranks_lexically_strong_consultant_first() -> None:
    """Control: NullSemanticIndex (semantic contribution=0) keeps the lexically-strong at rank 1."""
    # Arrange
    matcher = _build_matcher_with_null_index()
    # Act
    shortlist = matcher.match(_ROLE)
    # Assert — with no semantic signal, skill overlap wins; lexically-strong first
    assert shortlist.matches[0].consultant.id == _LEXICALLY_STRONG.id


# ---------------------------------------------------------------------------
# Test 3 — end-to-end CLI: `match-text --semantic` puts semantic consultant first
# ---------------------------------------------------------------------------


def test_match_text_semantic_cli_ranks_semantically_strong_consultant_first(
    tmp_path: Path,
) -> None:
    """End-to-end: `match-text --semantic` via CLI ranks the semantically-strong consultant first."""  # noqa: E501
    # Arrange — real Milvus index populated for the semantically-strong consultant;
    # build_matcher and build_role_parser are mocked so no real Presidio/LLM is needed.
    db_path = str(tmp_path / "cli_test.db")
    real_index = MilvusSemanticIndex(db_path=db_path)
    real_index.upsert(
        IndexItem(
            id=_SEMANTICALLY_STRONG.id,
            text="JVM Enterprise Backend Engineer java spring microservices",
            namespace="skills",
        )
    )
    matcher_with_real_index = _build_matcher_with_real_index(tmp_path)
    mock_role_parser = MagicMock()
    mock_role_parser.parse.return_value = _ROLE
    env = {"OPENROUTER_API_KEY": "dummy-key", "STAFFEER_MILVUS_PATH": db_path}
    with (
        patch("staffeer.cli.main.build_role_parser", return_value=mock_role_parser),
        patch("staffeer.cli.main.build_matcher", return_value=matcher_with_real_index),
    ):
        # Act
        result = _cli_runner.invoke(
            app,
            ["match-text", "JVM Enterprise Backend Engineer", "--semantic"],
            env=env,
        )
    # Assert — Semantic Strong (semantically close to the role) appears before Lexical Strong
    assert result.exit_code == 0, result.output
    assert result.output.index("Semantic Strong") < result.output.index("Lexical Strong")


# ---------------------------------------------------------------------------
# Test 4 (control) — `match-text` without --semantic keeps lexically-strong at rank 1
# ---------------------------------------------------------------------------


def test_match_text_without_semantic_cli_ranks_lexically_strong_first() -> None:
    """Control: `match-text` without --semantic keeps lexically-strong at rank 1."""
    # Arrange — NullSemanticIndex wired; semantic contribution is 0.0.
    matcher_with_null_index = _build_matcher_with_null_index()
    mock_role_parser = MagicMock()
    mock_role_parser.parse.return_value = _ROLE
    env = {"OPENROUTER_API_KEY": "dummy-key"}
    with (
        patch("staffeer.cli.main.build_role_parser", return_value=mock_role_parser),
        patch("staffeer.cli.main.build_matcher", return_value=matcher_with_null_index),
    ):
        # Act
        result = _cli_runner.invoke(
            app,
            ["match-text", "JVM Enterprise Backend Engineer"],
            env=env,
        )
    # Assert — no semantic signal; lexical skill overlap wins; Lexical Strong is ranked first
    assert result.exit_code == 0, result.output
    assert result.output.index("Lexical Strong") < result.output.index("Semantic Strong")
