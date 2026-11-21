"""Kiểm thử giới hạn tài nguyên đầu vào của API phân tích."""

import dataclasses

import app as app_module
import src.core.database as database_module
import src.core.facade as facade_module
from fastapi.testclient import TestClient

from app import app
from src.core.config import AppConfig
from tests.helpers import analyze_and_wait


def _config_with(**overrides) -> AppConfig:
    return dataclasses.replace(AppConfig.from_env({}), **overrides)


def test_upload_over_file_limit_returns_413(monkeypatch):
    monkeypatch.setattr(
        app_module, "get_config", lambda: _config_with(max_file_size_bytes=1024 * 1024)
    )

    client = TestClient(app)
    response = client.post(
        "/api/analyze",
        data={"provider": "local_nlp"},
        files={"file": ("big.txt", b"A" * (1024 * 1024 + 1), "text/plain")},
    )

    assert response.status_code == 413
    assert "giới hạn" in response.json()["detail"]


def test_raw_text_over_char_limit_returns_413(monkeypatch):
    monkeypatch.setattr(
        app_module, "get_config", lambda: _config_with(max_raw_text_chars=20)
    )

    client = TestClient(app)
    response = client.post(
        "/api/analyze",
        data={"provider": "local_nlp", "raw_text": "Y" * 21},
    )

    assert response.status_code == 413
    assert "vượt giới hạn" in response.json()["detail"]


def test_analysis_truncates_requirements_and_reports_warning(monkeypatch):
    config = _config_with(max_requirements=2, database_path=":memory:")
    monkeypatch.setattr(app_module, "get_config", lambda: config)
    monkeypatch.setattr(facade_module, "get_config", lambda: config)
    monkeypatch.setattr(database_module, "get_config", lambda: config)

    client = TestClient(app)
    payload = analyze_and_wait(
        client,
        {
            "provider": "local_nlp",
            "raw_text": (
                "Người dùng có thể đăng nhập bằng email. "
                "Hệ thống phải sao lưu dữ liệu hằng ngày. "
                "Quản trị viên có thể khóa tài khoản. "
                "Hệ thống phải gửi email thông báo."
            ),
        },
    )

    assert len(payload["requirements"]) == 2
    assert payload["warnings"]
    assert "2 câu đầu tiên" in payload["warnings"][0]
