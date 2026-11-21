"""Cấu hình ứng dụng đọc một lần từ biến môi trường.

Tập trung toàn bộ hằng số cấu hình (provider mặc định, model từng provider,
ngưỡng tin cậy, đường dẫn SQLite) để backend, classifier và frontend dùng chung
một nguồn sự thật. Giá trị sai được fallback an toàn kèm cảnh báo log.
"""

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, Mapping, Optional

logger = logging.getLogger(__name__)

PROVIDER_CONFIGS: Dict[str, dict] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "env_key": "OPENROUTER_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-1.5-flash",
        "env_key": "GEMINI_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
        "env_key": None,
    },
}

SUPPORTED_PROVIDERS = tuple(PROVIDER_CONFIGS)
LOCAL_PROVIDERS = ("local_nlp", "offline")
PROVIDER_ALIASES = {"offline": "local_nlp"}

DEFAULT_PROVIDER = "groq"
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
DEFAULT_DATABASE_PATH = "reqassist.db"


def _parse_confidence_threshold(raw_value: Optional[str], default: float) -> float:
    """Đọc ngưỡng tin cậy trong khoảng [0, 1], fallback kèm cảnh báo nếu sai."""
    if raw_value is None or str(raw_value).strip() == "":
        return default
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        logger.warning("CONFIDENCE_THRESHOLD=%r không phải số, dùng mặc định %.2f.", raw_value, default)
        return default
    if not 0.0 <= value <= 1.0:
        logger.warning("CONFIDENCE_THRESHOLD=%r ngoài khoảng [0, 1], dùng mặc định %.2f.", raw_value, default)
        return default
    return value


def _parse_provider(raw_value: Optional[str]) -> str:
    """Chuẩn hóa DEFAULT_PROVIDER; provider lạ fallback về groq."""
    candidate = (raw_value or "").strip().lower()
    candidate = PROVIDER_ALIASES.get(candidate, candidate)
    if candidate in SUPPORTED_PROVIDERS or candidate in LOCAL_PROVIDERS:
        return candidate
    if raw_value is not None and str(raw_value).strip():
        logger.warning("DEFAULT_PROVIDER=%r không hợp lệ, dùng %r.", raw_value, DEFAULT_PROVIDER)
    return DEFAULT_PROVIDER


@dataclass(frozen=True)
class AppConfig:
    """Cấu hình bất biến của ứng dụng, tạo từ biến môi trường."""

    default_provider: str = DEFAULT_PROVIDER
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    database_path: str = DEFAULT_DATABASE_PATH
    models: Mapping[str, str] = field(
        default_factory=lambda: {name: cfg["default_model"] for name, cfg in PROVIDER_CONFIGS.items()}
    )

    def model_for(self, provider: str) -> str:
        """Trả về model đã cấu hình cho provider, fallback về default của provider đó."""
        normalized = PROVIDER_ALIASES.get((provider or "").lower().strip(), (provider or "").lower().strip())
        if normalized in self.models:
            return self.models[normalized]
        return PROVIDER_CONFIGS["groq"]["default_model"]

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None) -> "AppConfig":
        """Tạo cấu hình từ mapping env (mặc định os.environ)."""
        env = os.environ if environ is None else environ

        models = {}
        for name, provider_cfg in PROVIDER_CONFIGS.items():
            raw_model = (env.get(f"{name.upper()}_MODEL") or "").strip()
            models[name] = raw_model or provider_cfg["default_model"]

        database_path = (env.get("DATABASE_PATH") or "").strip() or DEFAULT_DATABASE_PATH

        return cls(
            default_provider=_parse_provider(env.get("DEFAULT_PROVIDER")),
            confidence_threshold=_parse_confidence_threshold(
                env.get("CONFIDENCE_THRESHOLD"), DEFAULT_CONFIDENCE_THRESHOLD
            ),
            database_path=database_path,
            models=models,
        )


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Trả về cấu hình đã đọc một lần cho toàn bộ tiến trình."""
    return AppConfig.from_env()


def reset_config() -> None:
    """Xóa cache cấu hình (dùng khi env thay đổi trong kiểm thử)."""
    get_config.cache_clear()
