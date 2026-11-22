"""Cổng kết nối LLM đa nhà cung cấp sử dụng chuẩn OpenAI-compatible SDK.

Hỗ trợ kết nối trực tiếp tới Groq, OpenRouter, Google Gemini và Ollama
với kiểm tra khóa API thực tế nghiêm ngặt (loại bỏ hoàn toàn placeholder/mock key).
"""

import os
import re
import socket
from typing import Optional
from openai import OpenAI

from src.core.config import PROVIDER_CONFIGS, get_config

INVALID_KEY_MARKERS = (
    "placeholder",
    "your_",
    "_here",
    "example",
    "xxxx",
    "test_key_only",
)

RETIRED_GROQ_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
}
ACTIVE_GROQ_DEFAULT_MODEL = "qwen/qwen3.8-27b"
GROQ_FALLBACK_POOL = (
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
)


def is_ollama_running(host: str = "127.0.0.1", port: int = 11434, timeout: float = 0.25) -> bool:
    """Kiểm tra nhanh xem dịch vụ Ollama cục bộ có đang mở cổng 11434 trên máy hay không."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_real_api_key(api_key: Optional[str]) -> bool:
    """Kiểm tra khóa API có phải khóa thực tế hay chỉ là chuỗi mẫu placeholder."""
    if not api_key:
        return False
    cleaned = api_key.strip()
    if len(cleaned) < 8:
        return False
    lower_val = cleaned.lower()
    if any(marker in lower_val for marker in INVALID_KEY_MARKERS):
        return False
    return True


def strip_json_fences(raw_text: str) -> str:
    """Loại bỏ cặp thẻ markdown ```json ... ``` nếu mô hình trả về kèm định dạng code block."""
    if not raw_text:
        return ""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


class MultiLLMClient:
    """Đóng gói việc khởi tạo và tương tác với các LLM Provider tương thích OpenAI."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 25.0,
    ):
        app_config = get_config()
        self.provider = (provider or app_config.default_provider).lower().strip()
        config = PROVIDER_CONFIGS.get(self.provider, PROVIDER_CONFIGS["groq"])

        if not api_key and config["env_key"]:
            env_val = os.getenv(config["env_key"], "")
            if is_real_api_key(env_val):
                api_key = env_val

        self.api_key = api_key.strip() if (api_key and is_real_api_key(api_key)) else ""
        self.base_url = config["base_url"]
        self.model_name = model_name or app_config.model_for(self.provider)
        self.timeout = timeout

        self.client = OpenAI(
            api_key=self.api_key or "unconfigured_key",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=0,
        )
        self._groq_call_index = 0

    def is_configured(self) -> bool:
        """Kiểm tra xem khóa API thực sự hoặc dịch vụ Ollama đã sẵn sàng hay chưa."""
        if self.provider == "ollama":
            return is_ollama_running()
        if self.provider in ("offline", "local_nlp"):
            return False
        return is_real_api_key(self.api_key)

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 750,
    ) -> str:
        """Gửi truy vấn tới LLM API thật và trả về chuỗi JSON sạch.

        Hỗ trợ xoay vòng model dự phòng trên Groq khi chạm hạn mức OTPM.
        """
        if not self.is_configured():
            raise RuntimeError(
                f"Chưa cấu hình API Key hợp lệ cho cổng '{self.provider}'. "
                "Vui lòng nhập API Key thực tế để phân tích."
            )
        effective_model = self.model_name
        if self.provider == "groq" and effective_model in RETIRED_GROQ_MODELS:
            effective_model = ACTIVE_GROQ_DEFAULT_MODEL

        candidate_models = [effective_model]
        if self.provider == "groq":
            pool = list(GROQ_FALLBACK_POOL)
            if effective_model not in pool:
                pool.insert(0, effective_model)
            # Xoay vòng (Round-Robin) qua các model Groq để phân tải đều hạn mức 1000 OTPM / model
            start_idx = self._groq_call_index % len(pool)
            self._groq_call_index += 1
            candidate_models = pool[start_idx:] + pool[:start_idx]

        last_exc: Optional[Exception] = None
        for model_id in candidate_models:
            try:
                kwargs = {
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                }
                if self.provider == "groq" and max_tokens:
                    kwargs["max_tokens"] = min(max_tokens, 480)
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                return strip_json_fences(content)
            except Exception as exc:
                last_exc = exc
                err_str = str(exc).lower()
                # Nếu gặp lỗi giới hạn token/rate-limit (429 / OTPM / TPM) hoặc model ngừng hỗ trợ
                # trên Groq -> tự xoay sang model kế tiếp trong pool
                if self.provider == "groq" and any(
                    k in err_str
                    for k in ("429", "rate_limit", "too large", "otpm", "tpm", "decommissioned", "not_found")
                ):
                    continue
                raise

        if last_exc is not None:
            raise last_exc
        return ""
