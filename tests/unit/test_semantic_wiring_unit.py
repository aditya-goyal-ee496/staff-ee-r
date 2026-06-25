"""Unit tests for slice 05a — semantic blend wiring.

Covers:
- I1: StaffeerConfig.weights has explicit default keys (skills, soft_llm, semantic).
- I2/I3: CLI `match --semantic` guard: exits 1 with error when STAFFEER_MILVUS_PATH unset.
- I2/I4: CLI `match-text --semantic` guard: exits 1 with error when STAFFEER_MILVUS_PATH unset.
- I5: _semantic_config merges semantic_enabled=True into config when milvus_path is present.
- N1: `match --semantic` with valid STAFFEER_MILVUS_PATH but unknown role ID exits 1.

One assertion per test; AAA layout; no mocking of domain logic.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from staffeer.cli.main import _semantic_config, app
from staffeer.config import StaffeerConfig

runner = CliRunner()


# ---------------------------------------------------------------------------
# I1 — StaffeerConfig.weights explicit defaults
# ---------------------------------------------------------------------------


def test_staffeer_config_weights_skills_default_is_1_0() -> None:
    """I1: 'skills' weight defaults to 1.0 via default_factory, not absent."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert
    assert config.weights["skills"] == 1.0


def test_staffeer_config_weights_soft_llm_default_is_1_0() -> None:
    """I1: 'soft_llm' weight defaults to 1.0 via default_factory."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert
    assert config.weights["soft_llm"] == 1.0


def test_staffeer_config_weights_semantic_default_is_1_0() -> None:
    """I1: 'semantic' weight defaults to 1.0 via default_factory."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert
    assert config.weights["semantic"] == 1.0


def test_staffeer_config_weights_has_exactly_three_default_keys() -> None:
    """I1: Default weights contain exactly the three expected keys — no extras, none missing."""
    # Arrange / Act
    config = StaffeerConfig()
    # Assert
    assert set(config.weights.keys()) == {"skills", "soft_llm", "semantic"}


# ---------------------------------------------------------------------------
# I5 — _semantic_config positive path: merges semantic_enabled=True
# ---------------------------------------------------------------------------


def test_semantic_config_returns_config_with_semantic_enabled_true_when_milvus_path_present() -> (
    None
):
    """I5: _semantic_config sets semantic_enabled=True when milvus_path is present."""
    # Arrange
    config = StaffeerConfig(milvus_path="/tmp/test.db")
    # Act
    result = _semantic_config(config)
    # Assert
    assert result.semantic_enabled is True


# ---------------------------------------------------------------------------
# I2 / I3 — `match --semantic` guard: exits 1 when milvus_path unset
# ---------------------------------------------------------------------------


def test_match_semantic_flag_exits_1_when_milvus_path_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I2/I3: `match --semantic` exits 1 when STAFFEER_MILVUS_PATH is not set."""

    # Arrange — ensure STAFFEER_MILVUS_PATH is absent from the environment
    monkeypatch.delenv("STAFFEER_MILVUS_PATH", raising=False)
    # Act
    result = runner.invoke(app, ["match", "ROLE-01", "--semantic"])
    # Assert
    assert result.exit_code == 1


def test_match_semantic_flag_prints_milvus_error_message_to_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I2/I3: `match --semantic` without STAFFEER_MILVUS_PATH reports an error on stderr."""

    # Arrange
    monkeypatch.delenv("STAFFEER_MILVUS_PATH", raising=False)
    # Act
    result = runner.invoke(app, ["match", "ROLE-01", "--semantic"])
    # Assert — error must appear on stderr (not stdout) and name the missing env var
    assert "STAFFEER_MILVUS_PATH" in result.stderr or "milvus" in result.stderr.lower()


# ---------------------------------------------------------------------------
# I2 / I4 — `match-text --semantic` guard: exits 1 when milvus_path unset
# ---------------------------------------------------------------------------


def test_match_text_semantic_flag_exits_1_when_milvus_path_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I2/I4: `match-text --semantic` exits 1 when STAFFEER_MILVUS_PATH is not set."""

    # Arrange — milvus path absent; openrouter key present so llm guard does not fire first
    monkeypatch.delenv("STAFFEER_MILVUS_PATH", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-key")
    # Act
    result = runner.invoke(app, ["match-text", "senior python engineer", "--semantic"])
    # Assert
    assert result.exit_code == 1


def test_match_text_semantic_flag_prints_milvus_error_message_to_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I2/I4: `match-text --semantic` without STAFFEER_MILVUS_PATH reports an error on stderr."""

    # Arrange
    monkeypatch.delenv("STAFFEER_MILVUS_PATH", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy-key")
    # Act
    result = runner.invoke(app, ["match-text", "senior python engineer", "--semantic"])
    # Assert — error must appear on stderr (not stdout) and name the missing env var
    assert "STAFFEER_MILVUS_PATH" in result.stderr or "milvus" in result.stderr.lower()


# ---------------------------------------------------------------------------
# N1 — `match --semantic` post-guard: unknown role ID exits 1
# ---------------------------------------------------------------------------


def test_match_semantic_exits_1_when_role_id_does_not_exist(
    monkeypatch: pytest.MonkeyPatch,
    workbook_factory: Callable[..., Path],
    tmp_path: Path,
) -> None:
    """N1: --semantic with a valid STAFFEER_MILVUS_PATH exits 1 when role ID is not found.

    This confirms the semantic milvus guard passes (milvus_path is set) and the
    subsequent role-not-found path still exits with code 1 as expected.
    """
    # Arrange — set milvus_path so the semantic guard passes; provide an empty workbook
    milvus_path = str(tmp_path / "test.db")
    monkeypatch.setenv("STAFFEER_MILVUS_PATH", milvus_path)
    path = workbook_factory()  # no roles in workbook
    # Act
    result = runner.invoke(app, ["match", "ROLE-NONEXISTENT", "--semantic", "--data", str(path)])
    # Assert
    assert result.exit_code == 1
