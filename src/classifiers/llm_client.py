"""Cổng kết nối LLM đa nhà cung cấp sử dụng chuẩn OpenAI-compatible SDK.

Hỗ trợ chuyển đổi nhanh giữa Groq, OpenRouter, Gemini và Ollama thông qua
thay đổi base_url, api_key và model_name.
"""

import os
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


class MultiLLMClient:
    """Đóng gói việc khởi tạo và tương tác với các LLM Provider tương thích OpenAI."""

    def __init__(
        self,
        provider: str = "groq",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 8.0,
    ):
        self.provider = provider.lower().strip()
        config = PROVIDER_CONFIGS.get(self.provider, PROVIDER_CONFIGS["groq"])

        # Lấy API Key từ tham số hoặc biến môi trường
        if not api_key and config["env_key"]:
            api_key = os.getenv(config["env_key"])

        self.api_key = api_key or "placeholder_key"
        self.base_url = config["base_url"]
        self.model_name = model_name or config["default_model"]
        self.timeout = timeout

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=2,
        )

    def is_configured(self) -> bool:
        """Kiểm tra xem khóa API đã được cung cấp thực sự hay chưa."""
        if self.provider == "ollama":
            return True
        return bool(self.api_key and not self.api_key.startswith("placeholder_") and len(self.api_key) > 5)

    def chat_completion(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        """Gửi truy vấn và nhận văn bản JSON trả về từ mô hình."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""
