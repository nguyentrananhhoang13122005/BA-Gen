"""Kiểm thử cấu hình ứng dụng đọc từ biến môi trường."""

from src.core.config import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_DATABASE_PATH,
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_MAX_RAW_TEXT_CHARS,
    DEFAULT_MAX_REQUIREMENTS,
    AppConfig,
    get_config,
    reset_config,
)
from src.core.database import DatabaseManager


def test_config_defaults_when_env_empty():
    config = AppConfig.from_env({})

    assert config.default_provider == "groq"
    assert config.confidence_threshold == DEFAULT_CONFIDENCE_THRESHOLD
    assert config.database_path == DEFAULT_DATABASE_PATH
    assert config.model_for("groq") == "llama-3.3-70b-versatile"
    assert config.model_for("gemini") == "gemini-1.5-flash"


def test_config_reads_env_overrides():
    config = AppConfig.from_env({
        "DEFAULT_PROVIDER": "OpenRouter",
        "OPENROUTER_MODEL": "custom/model-free",
        "CONFIDENCE_THRESHOLD": "0.6",
        "DATABASE_PATH": "data/custom.db",
    })

    assert config.default_provider == "openrouter"
    assert config.model_for("openrouter") == "custom/model-free"
    assert config.confidence_threshold == 0.6
    assert config.database_path == "data/custom.db"


def test_config_falls_back_on_invalid_values():
    config = AppConfig.from_env({
        "DEFAULT_PROVIDER": "khong_ton_tai",
        "CONFIDENCE_THRESHOLD": "1.5",
    })
    assert config.default_provider == "groq"
    assert config.confidence_threshold == DEFAULT_CONFIDENCE_THRESHOLD

    config = AppConfig.from_env({"CONFIDENCE_THRESHOLD": "khong-phai-so"})
    assert config.confidence_threshold == DEFAULT_CONFIDENCE_THRESHOLD


def test_config_supports_offline_alias():
    config = AppConfig.from_env({"DEFAULT_PROVIDER": "offline"})
    assert config.default_provider == "local_nlp"


def test_get_config_reads_environment_and_can_reset(monkeypatch):
    reset_config()
    monkeypatch.setenv("DEFAULT_PROVIDER", "gemini")
    try:
        assert get_config().default_provider == "gemini"
    finally:
        reset_config()


def test_config_reads_resource_limits():
    config = AppConfig.from_env({
        "MAX_FILE_SIZE_BYTES": "1048576",
        "MAX_RAW_TEXT_CHARS": "5000",
        "MAX_REQUIREMENTS": "20",
    })

    assert config.max_file_size_bytes == 1048576
    assert config.max_raw_text_chars == 5000
    assert config.max_requirements == 20

    invalid = AppConfig.from_env({
        "MAX_FILE_SIZE_BYTES": "abc",
        "MAX_RAW_TEXT_CHARS": "-1",
        "MAX_REQUIREMENTS": "0",
    })
    assert invalid.max_file_size_bytes == DEFAULT_MAX_FILE_SIZE_BYTES
    assert invalid.max_raw_text_chars == DEFAULT_MAX_RAW_TEXT_CHARS
    assert invalid.max_requirements == DEFAULT_MAX_REQUIREMENTS


def test_config_reads_auth_cors_and_rate_limits():
    config = AppConfig.from_env({
        "APP_PASSWORD": " mat-khau ",
        "CORS_ORIGINS": "http://localhost:5173, https://app.example.com/,*",
        "ANALYZE_RATE_LIMIT_PER_MINUTE": "3",
        "AUTH_RATE_LIMIT_PER_MINUTE": "2",
        "COOKIE_SECURE": "true",
    })

    assert config.app_password == "mat-khau"
    assert config.cors_origins == ("http://localhost:5173", "https://app.example.com")
    assert config.analyze_rate_limit_per_minute == 3
    assert config.auth_rate_limit_per_minute == 2
    assert config.session_cookie_secure is True


def test_config_cors_wildcard_falls_back_to_defaults():
    assert AppConfig.from_env({"CORS_ORIGINS": "*"}).cors_origins == DEFAULT_CORS_ORIGINS
    assert AppConfig.from_env({}).app_password is None


def test_database_manager_uses_configured_path(tmp_path, monkeypatch):
    custom_db = tmp_path / "custom.db"
    reset_config()
    monkeypatch.setenv("DATABASE_PATH", str(custom_db))
    try:
        db = DatabaseManager()
        assert db.db_path == str(custom_db)
        assert custom_db.exists()
    finally:
        reset_config()
