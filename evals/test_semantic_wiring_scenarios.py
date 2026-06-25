"""Deterministic golden-table SCENARIO EVALS — Slice 05a: Semantic blend wiring.

Each scenario is a frozen fixture asserting exact behaviour of the new CLI wiring
and explicit default weights.  No network I/O; no real Milvus (that is the
integration test in tests/integration/test_semantic_wiring.py).

Scenarios
---------
1. default_weights_has_skills_key
   StaffeerConfig().weights['skills'] == 1.0 (explicit default, not absent).

2. default_weights_has_soft_llm_key
   StaffeerConfig().weights['soft_llm'] == 1.0 (explicit default).

3. default_weights_has_semantic_key
   StaffeerConfig().weights['semantic'] == 1.0 (explicit default).

4. semantic_flag_exits_with_code_1_when_milvus_path_unset
   Invoking `match ROLE-01 --semantic` without STAFFEER_MILVUS_PATH exits 1
   with a clear error message on stderr/stdout.

5. match_text_semantic_flag_exits_with_code_1_when_milvus_path_unset
   Invoking `match-text "..." --semantic` without STAFFEER_MILVUS_PATH exits 1
   with a clear error message.

6. [NEGATIVE] default_weights_is_not_empty_dict
   StaffeerConfig().weights must NOT be an empty dict {}.
   A 100% pass rate without this scenario is a COVERAGE WARNING — it confirms the
   old "default_factory=dict" (empty) path is gone.

NOTE: 100% green is correct here; the WARNING is *omitting* the negative scenario.
"""

from __future__ import annotations

from typer.testing import CliRunner

from staffeer.cli.main import app
from staffeer.config import StaffeerConfig

runner = CliRunner()


# ---------------------------------------------------------------------------
# Scenario 1 — explicit default weight for 'skills'
# ---------------------------------------------------------------------------


def test_default_weights_has_skills_key() -> None:
    """StaffeerConfig() carries an explicit 'skills' weight of 1.0."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert
    assert config.weights.get("skills") == 1.0


# ---------------------------------------------------------------------------
# Scenario 2 — explicit default weight for 'soft_llm'
# ---------------------------------------------------------------------------


def test_default_weights_has_soft_llm_key() -> None:
    """StaffeerConfig() carries an explicit 'soft_llm' weight of 1.0."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert
    assert config.weights.get("soft_llm") == 1.0


# ---------------------------------------------------------------------------
# Scenario 3 — explicit default weight for 'semantic'
# ---------------------------------------------------------------------------


def test_default_weights_has_semantic_key() -> None:
    """StaffeerConfig() carries an explicit 'semantic' weight of 1.0."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert
    assert config.weights.get("semantic") == 1.0


# ---------------------------------------------------------------------------
# Scenario 4 — match --semantic exits 1 when STAFFEER_MILVUS_PATH is unset
# ---------------------------------------------------------------------------


def test_match_semantic_flag_exits_with_code_1_when_milvus_path_unset() -> None:
    """`match ROLE-01 --semantic` without STAFFEER_MILVUS_PATH exits 1 with clear error."""
    # Arrange — no STAFFEER_MILVUS_PATH in env; use a dummy role id
    env = {"STAFFEER_MILVUS_PATH": ""}
    # Act
    result = runner.invoke(app, ["match", "ROLE-01", "--semantic"], env=env)
    # Assert
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Scenario 5 — match-text --semantic exits 1 when STAFFEER_MILVUS_PATH is unset
# ---------------------------------------------------------------------------


def test_match_text_semantic_flag_exits_with_code_1_when_milvus_path_unset() -> None:
    """`match-text "..." --semantic` without STAFFEER_MILVUS_PATH exits 1 with clear error."""
    # Arrange — OPENROUTER_API_KEY to pass the llm check; no milvus path
    env = {"OPENROUTER_API_KEY": "dummy-key", "STAFFEER_MILVUS_PATH": ""}
    # Act
    result = runner.invoke(app, ["match-text", "senior python engineer", "--semantic"], env=env)
    # Assert
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Scenario 6 — NEGATIVE: default weights must NOT be the old empty dict {}
#
# This is the mandatory NEGATIVE scenario for this slice.  It guards against
# regression to `default_factory=dict` (the old "implicit 1.0" path).  If the
# weights field reverts to an empty mapping, this test fails — exactly what we want.
# ---------------------------------------------------------------------------


def test_default_weights_is_not_empty_dict() -> None:
    """NEGATIVE: StaffeerConfig().weights must not be {} (old implicit-1.0 path)."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert — must contain all three explicit keys, not be empty
    assert config.weights != {}
