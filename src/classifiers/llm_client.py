"""Cổng kết nối LLM đa nhà cung cấp sử dụng chuẩn OpenAI-compatible SDK.

Hỗ trợ kết nối trực tiếp tới Groq, OpenRouter, Google Gemini và Ollama
với kiểm tra khóa API thực tế nghiêm ngặt (loại bỏ hoàn toàn placeholder/mock key).
"""

import os
import re
import socket
from typing import Optional
from openai import OpenAI


PROVIDER_CONFIGS = {
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

INVALID_KEY_MARKERS = (
    "placeholder",
    "your_",
    "_here",
    "example",
    "xxxx",
    "test_key_only",
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
        provider: str = "groq",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 25.0,
    ):
        self.provider = provider.lower().strip()
        config = PROVIDER_CONFIGS.get(self.provider, PROVIDER_CONFIGS["groq"])

        if not api_key and config["env_key"]:
            env_val = os.getenv(config["env_key"], "")
            if is_real_api_key(env_val):
                api_key = env_val

        self.api_key = api_key.strip() if (api_key and is_real_api_key(api_key)) else ""
        self.base_url = config["base_url"]
        self.model_name = model_name or config["default_model"]
        self.timeout = timeout

        self.client = OpenAI(
            api_key=self.api_key or "unconfigured_key",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=2,
        )

    def is_configured(self) -> bool:
        """Kiểm tra xem khóa API thực sự hoặc dịch vụ Ollama đã sẵn sàng hay chưa."""
        if self.provider == "ollama":
            return is_ollama_running()
        if self.provider in ("offline", "local_nlp"):
            return False
        return is_real_api_key(self.api_key)

    def chat_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """Gửi truy vấn tới LLM API thật và trả về chuỗi JSON sạch."""
        if not self.is_configured():
            raise RuntimeError(
                f"Chưa cấu hình API Key hợp lệ cho cổng '{self.provider}'. "
                "Vui lòng nhập API Key thực tế để phân tích."
            )
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return strip_json_fences(content)
