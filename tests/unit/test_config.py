import os
from pathlib import Path

import pytest

from staffeer.config import Settings, StaffeerConfig, load_env_file


def test_settings_default_to_none_when_env_absent() -> None:
    # Arrange / Act
    settings = Settings()

    # Assert
    assert settings.data_path is None


def test_data_path_uses_env_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("STAFFEER_DATA", "/custom/demand-supply.xlsx")

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.data_path == "/custom/demand-supply.xlsx"


def test_data_path_defaults_to_bundled_workbook_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    workbook = tmp_path / "demand-supply.xlsx"
    workbook.write_bytes(b"")
    monkeypatch.delenv("STAFFEER_DATA", raising=False)
    monkeypatch.setattr("staffeer.config.DEFAULT_DATA_FILE", workbook)

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.data_path == str(workbook)


def test_data_path_is_none_when_unset_and_workbook_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    monkeypatch.delenv("STAFFEER_DATA", raising=False)
    monkeypatch.setattr("staffeer.config.DEFAULT_DATA_FILE", tmp_path / "missing.xlsx")

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.data_path is None


def test_load_env_file_populates_environment_from_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    env_file = tmp_path / ".env"
    env_file.write_text("STAFFEER_DATA=/from/dotenv.xlsx\n")
    monkeypatch.delenv("STAFFEER_DATA", raising=False)

    # Act
    load_env_file(env_file)

    # Assert
    assert os.environ["STAFFEER_DATA"] == "/from/dotenv.xlsx"


def test_load_env_file_does_not_override_real_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    env_file = tmp_path / ".env"
    env_file.write_text("STAFFEER_DATA=/from/dotenv.xlsx\n")
    monkeypatch.setenv("STAFFEER_DATA", "/from/real-env.xlsx")

    # Act
    load_env_file(env_file)

    # Assert
    assert os.environ["STAFFEER_DATA"] == "/from/real-env.xlsx"


def test_profiles_enabled_defaults_to_false() -> None:
    # Arrange / Act
    config = StaffeerConfig()

    # Assert
    assert config.profiles_enabled is False


def test_feedback_dir_defaults_to_none() -> None:
    # Arrange / Act
    config = StaffeerConfig()

    # Assert
    assert config.feedback_dir is None


@pytest.mark.parametrize("truthy_value", ["1", "true", "True", "TRUE", "yes", "Yes", "YES"])
def test_profiles_enabled_is_true_for_truthy_env_values(
    monkeypatch: pytest.MonkeyPatch, truthy_value: str
) -> None:
    # Arrange
    monkeypatch.setenv("STAFFEER_PROFILES", truthy_value)

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.profiles_enabled is True


@pytest.mark.parametrize("falsy_value", ["false", "False", "FALSE", "0", "no", "No", "NO", ""])
def test_profiles_enabled_is_false_for_falsy_env_values(
    monkeypatch: pytest.MonkeyPatch, falsy_value: str
) -> None:
    # Arrange
    monkeypatch.setenv("STAFFEER_PROFILES", falsy_value)

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.profiles_enabled is False


def test_feedback_dir_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("STAFFEER_FEEDBACK_DIR", "/data/feedback")

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.feedback_dir == "/data/feedback"


def test_feedback_dir_is_none_when_env_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.delenv("STAFFEER_FEEDBACK_DIR", raising=False)

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.feedback_dir is None


def test_milvus_path_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("STAFFEER_MILVUS_PATH", "/data/milvus.db")

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.milvus_path == "/data/milvus.db"


def test_embedding_model_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("STAFFEER_EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.embedding_model == "sentence-transformers/all-mpnet-base-v2"


def test_embedding_model_defaults_to_all_minilm_when_env_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.delenv("STAFFEER_EMBEDDING_MODEL", raising=False)

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.embedding_model == "all-MiniLM-L6-v2"


def test_profiles_dir_uses_env_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("STAFFEER_PROFILES_DIR", "/custom/profiles")

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.profiles_dir == "/custom/profiles"


def test_profiles_dir_defaults_to_bundled_dir_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    monkeypatch.delenv("STAFFEER_PROFILES_DIR", raising=False)
    monkeypatch.setattr("staffeer.config.DEFAULT_PROFILES_DIR", profiles_dir)

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.profiles_dir == str(profiles_dir)


def test_profiles_dir_is_none_when_unset_and_bundled_dir_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Arrange
    monkeypatch.delenv("STAFFEER_PROFILES_DIR", raising=False)
    monkeypatch.setattr("staffeer.config.DEFAULT_PROFILES_DIR", tmp_path / "missing-profiles")

    # Act
    config = StaffeerConfig.from_env()

    # Assert
    assert config.profiles_dir is None
