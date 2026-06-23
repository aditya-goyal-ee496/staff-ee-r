from staffeer.config import Settings


def test_settings_default_to_none_when_env_absent() -> None:
    # Arrange / Act
    settings = Settings()

    # Assert
    assert settings.data_path is None
