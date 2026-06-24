import pytest

from staffeer.config import Settings, StaffeerConfig


def test_settings_default_to_none_when_env_absent() -> None:
    # Arrange / Act
    settings = Settings()

    # Assert
    assert settings.data_path is None


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
