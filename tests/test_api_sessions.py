"""Kiểm thử cô lập phiên người dùng và cookie phiên có chữ ký."""

import src.core.sessions as sessions_module
from fastapi.testclient import TestClient

from app import app
from src.core.sessions import SESSION_COOKIE_NAME, SessionManager, SessionState
from tests.helpers import analyze_and_wait


def _analyze(client: TestClient, text: str) -> dict:
    return analyze_and_wait(client, {"provider": "local_nlp", "raw_text": text})


def test_session_cookie_is_http_only_and_signed():
    client = TestClient(app)
    response = client.get("/api/config-defaults")

    set_cookie = response.headers.get("set-cookie", "")
    assert SESSION_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie


def test_two_sessions_do_not_share_analysis_data():
    client_a = TestClient(app)
    client_b = TestClient(app)

    result_a = _analyze(client_a, "Người dùng có thể đăng nhập bằng email và mật khẩu.")
    result_b = _analyze(client_b, "Hệ thống phải sao lưu dữ liệu hằng ngày lúc 2 giờ sáng.")

    assert result_a["project"]["project_id"] != result_b["project"]["project_id"]

    md_a = client_a.get("/api/export/srs-md").text
    md_b = client_b.get("/api/export/srs-md").text

    assert "đăng nhập" in md_a
    assert "sao lưu" not in md_a
    assert "sao lưu" in md_b
    assert "đăng nhập" not in md_b


def test_forged_cookie_does_not_access_existing_session():
    client_a = TestClient(app)
    _analyze(client_a, "Người dùng có thể đăng nhập bằng email và mật khẩu.")

    valid_token = client_a.cookies.get(SESSION_COOKIE_NAME)
    assert valid_token
    session_id, issued_at, _signature = valid_token.split(".")
    forged_token = f"{session_id}.{issued_at}.{'0' * 64}"

    attacker = TestClient(app)
    response = attacker.get(
        "/api/export/srs-md",
        headers={"Cookie": f"{SESSION_COOKIE_NAME}={forged_token}"},
    )

    assert response.status_code == 404


def test_session_expires_after_ttl(monkeypatch):
    monkeypatch.setattr(sessions_module.time, "time", lambda: 1000.0)
    manager = SessionManager(secret_key="test-secret", ttl_seconds=10, secure_cookie=False)
    token, state = manager.create()

    assert manager.resolve(token) is state
    assert manager.active_session_count() == 1

    monkeypatch.setattr(sessions_module.time, "time", lambda: 1011.0)
    assert manager.resolve(token) is None
    assert manager.active_session_count() == 0


def test_session_ids_are_unique_and_state_isolated():
    manager = SessionManager(secret_key="test-secret", ttl_seconds=60, secure_cookie=False)
    token_one, state_one = manager.create()
    token_two, state_two = manager.create()

    assert token_one != token_two
    assert state_one is not state_two
    assert manager.resolve(token_one) is state_one
    assert manager.resolve(token_two) is state_two


def test_session_state_tracks_auth_and_analyze_quota():
    state = SessionState(owner_id="owner", facade=object())

    assert state.authenticated is False
    state.authenticated = True
    assert state.authenticated is True

    assert state.check_analyze_rate(2) is True
    assert state.check_analyze_rate(2) is True
    assert state.check_analyze_rate(2) is False


def test_analyze_quota_window_slides(monkeypatch):
    state = SessionState(owner_id="owner", facade=object())
    monkeypatch.setattr(sessions_module.time, "time", lambda: 100.0)
    assert state.check_analyze_rate(1) is True
    assert state.check_analyze_rate(1) is False

    monkeypatch.setattr(sessions_module.time, "time", lambda: 161.0)
    assert state.check_analyze_rate(1) is True


def test_manager_invalidate_removes_session():
    manager = SessionManager(secret_key="test-secret", ttl_seconds=60, secure_cookie=False)
    token, _state = manager.create()

    manager.invalidate(token)

    assert manager.resolve(token) is None
    assert manager.active_session_count() == 0
