"""Kiểm thử đăng nhập, CORS, phạm vi fallback API key và rate-limit."""

import dataclasses
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app as app_module
import src.core.database as database_module
import src.core.facade as facade_module
from app import app
from src.core.config import AppConfig, get_config
from tests.helpers import analyze_and_wait


def _config(**overrides) -> AppConfig:
    return dataclasses.replace(AppConfig.from_env({}), **overrides)


def _patch_config(monkeypatch, config: AppConfig) -> None:
    monkeypatch.setattr(app_module, "get_config", lambda: config)
    monkeypatch.setattr(facade_module, "get_config", lambda: config)
    monkeypatch.setattr(database_module, "get_config", lambda: config)


@pytest.fixture(autouse=True)
def _reset_login_limiter():
    app_module.login_limiter.reset()
    yield
    app_module.login_limiter.reset()


def test_protected_endpoints_require_login(monkeypatch):
    _patch_config(monkeypatch, _config(app_password="mat-khau-manh"))
    client = TestClient(app)

    status = client.get("/api/auth/status")
    assert status.status_code == 200
    assert status.json()["auth_required"] is True
    assert status.json()["authenticated"] is False

    assert client.get("/api/config-defaults").status_code == 401
    assert client.get("/api/export/srs-md").status_code == 401
    assert client.post(
        "/api/analyze", data={"provider": "local_nlp", "raw_text": "Người dùng có thể đăng nhập."}
    ).status_code == 401


def test_login_success_unlocks_api_and_logout_relocks(monkeypatch):
    _patch_config(monkeypatch, _config(app_password="mat-khau-manh"))
    client = TestClient(app)

    wrong = client.post("/api/auth/login", json={"password": "sai-mat-khau"})
    assert wrong.status_code == 401

    login = client.post("/api/auth/login", json={"password": "mat-khau-manh"})
    assert login.status_code == 200
    assert login.json()["authenticated"] is True
    assert client.get("/api/auth/status").json()["authenticated"] is True
    assert client.get("/api/config-defaults").status_code == 200

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["authenticated"] is False
    assert client.get("/api/auth/status").json()["authenticated"] is False
    assert client.get("/api/config-defaults").status_code == 401


def test_wrong_password_is_rate_limited(monkeypatch):
    _patch_config(
        monkeypatch,
        _config(app_password="mat-khau-manh", auth_rate_limit_per_minute=2),
    )
    client = TestClient(app)

    assert client.post("/api/auth/login", json={"password": "sai-1"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": "sai-2"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": "sai-3"}).status_code == 429
    assert client.post("/api/auth/login", json={"password": "mat-khau-manh"}).status_code == 429


def test_auth_disabled_keeps_local_mode_open(monkeypatch):
    _patch_config(monkeypatch, _config(database_path=":memory:"))
    client = TestClient(app)

    status = client.get("/api/auth/status").json()
    assert status["auth_required"] is False
    assert status["authenticated"] is True
    assert client.get("/api/config-defaults").status_code == 200


def test_cors_allows_only_configured_origins():
    allowed_origin = get_config().cors_origins[0]
    client = TestClient(app)

    allowed = client.get("/api/auth/status", headers={"Origin": allowed_origin})
    assert allowed.headers.get("access-control-allow-origin") == allowed_origin

    denied = client.get(
        "/api/auth/status", headers={"Origin": "https://evil.example"}
    )
    assert "access-control-allow-origin" not in denied.headers


def test_env_key_is_scoped_to_localhost_or_authenticated():
    remote_request = SimpleNamespace(client=SimpleNamespace(host="203.0.113.7"))
    local_request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    anonymous = SimpleNamespace(authenticated=False)
    authenticated = SimpleNamespace(authenticated=True)

    assert app_module._can_use_env_key(remote_request, anonymous) is False
    assert app_module._can_use_env_key(remote_request, authenticated) is True
    assert app_module._can_use_env_key(local_request, anonymous) is True


def test_public_request_cannot_spend_server_env_key(monkeypatch):
    _patch_config(monkeypatch, _config(database_path=":memory:"))
    monkeypatch.setenv("GROQ_API_KEY", "gsk_live_abc123456789")
    client = TestClient(app)

    response = client.post(
        "/api/analyze",
        data={"provider": "groq", "raw_text": "Người dùng có thể đăng nhập."},
    )

    assert response.status_code == 400
    assert "API Key" in response.json()["detail"]


def test_analyze_rate_limit_returns_429(monkeypatch):
    _patch_config(
        monkeypatch,
        _config(analyze_rate_limit_per_minute=1, database_path=":memory:"),
    )
    client = TestClient(app)
    body = {
        "provider": "local_nlp",
        "raw_text": "Người dùng có thể đăng nhập bằng email và mật khẩu.",
    }

    analyze_and_wait(client, body)
    limited = client.post("/api/analyze", data=body)

    assert limited.status_code == 429
    assert "1 lần" in limited.json()["detail"]
