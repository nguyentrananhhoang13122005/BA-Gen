"""Quản lý phiên phân tích độc lập theo từng người dùng.

Mỗi phiên sở hữu một RequirementsAnalysisFacade riêng và một khóa chống race.
Phiên được nhận diện bằng cookie HttpOnly có chữ ký HMAC và hết hạn sau TTL;
cookie giả hoặc phiên đã hết hạn đều bị từ chối để tạo phiên mới.
"""

import hashlib
import hmac
import logging
import secrets
import threading
import time
from collections import deque
from typing import Dict, Optional, Tuple

from src.classifiers.llm_client import MultiLLMClient
from src.core.config import get_config
from src.core.facade import RequirementAnalysisFacade

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "ba_gen_session"


class SessionState:
    """Trạng thái riêng của một phiên: facade, xác thực và khóa chống race."""

    ANALYZE_WINDOW_SECONDS = 60

    def __init__(
        self,
        owner_id: Optional[str] = None,
        facade: Optional[RequirementAnalysisFacade] = None,
    ):
        self.owner_id = owner_id
        self.facade = facade or RequirementAnalysisFacade(
            llm_client=MultiLLMClient(provider="local_nlp"),
            owner_id=owner_id,
        )
        self.authenticated = False
        self._analyze_timestamps: deque = deque()
        self.lock = threading.RLock()

    def check_analyze_rate(self, limit_per_minute: int) -> bool:
        """Ghi nhận một lượt analyze nếu chưa vượt hạn mức trượt 60 giây.

        Gọi trong khi đang giữ ``self.lock`` để tránh đếm trùng giữa các request.
        """
        now = time.time()
        while (
            self._analyze_timestamps
            and now - self._analyze_timestamps[0] >= self.ANALYZE_WINDOW_SECONDS
        ):
            self._analyze_timestamps.popleft()
        if len(self._analyze_timestamps) >= limit_per_minute:
            return False
        self._analyze_timestamps.append(now)
        return True


class SessionManager:
    """Tạo, xác thực và dọn dẹp phiên người dùng."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        secure_cookie: Optional[bool] = None,
    ):
        config = get_config()
        resolved_secret = secret_key or config.secret_key
        if not resolved_secret:
            resolved_secret = secrets.token_hex(32)
            logger.warning(
                "Chưa cấu hình SECRET_KEY; dùng khóa ngẫu nhiên cho tiến trình này. "
                "Phiên sẽ không còn hiệu lực sau khi khởi động lại máy chủ."
            )
        self._secret = resolved_secret.encode("utf-8")
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else config.session_ttl_seconds
        self.secure_cookie = (
            config.session_cookie_secure if secure_cookie is None else secure_cookie
        )
        self._entries: Dict[str, Tuple[int, SessionState]] = {}
        self._lock = threading.Lock()

    def _sign(self, session_id: str, issued_at: int) -> str:
        payload = f"{session_id}.{issued_at}".encode("utf-8")
        return hmac.new(self._secret, payload, hashlib.sha256).hexdigest()

    def _parse_token(self, token: Optional[str]) -> Optional[str]:
        """Xác thực chữ ký và hạn dùng của cookie, trả về session_id hợp lệ."""
        if not token:
            return None
        parts = token.split(".")
        if len(parts) != 3:
            return None
        session_id, issued_raw, signature = parts
        try:
            issued_at = int(issued_raw)
        except ValueError:
            return None
        expected = self._sign(session_id, issued_at)
        if not hmac.compare_digest(signature, expected):
            return None
        if time.time() - issued_at > self.ttl_seconds:
            return None
        return session_id

    def create(self) -> Tuple[str, SessionState]:
        """Tạo phiên mới, trả về (cookie token, trạng thái phiên)."""
        session_id = secrets.token_urlsafe(32)
        issued_at = int(time.time())
        token = f"{session_id}.{issued_at}.{self._sign(session_id, issued_at)}"
        state = SessionState(owner_id=session_id)
        with self._lock:
            self._purge_expired_locked()
            self._entries[session_id] = (issued_at, state)
        return token, state

    def resolve(self, token: Optional[str]) -> Optional[SessionState]:
        """Trả về phiên nếu cookie hợp lệ và còn hạn, ngược lại None."""
        session_id = self._parse_token(token)
        if not session_id:
            return None
        with self._lock:
            self._purge_expired_locked()
            entry = self._entries.get(session_id)
            return entry[1] if entry else None

    def get_or_create(self, token: Optional[str]) -> Tuple[SessionState, Optional[str]]:
        """Lấy phiên hiện tại hoặc tạo phiên mới nếu cookie thiếu/không hợp lệ."""
        state = self.resolve(token)
        if state is not None:
            return state, None
        new_token, new_state = self.create()
        return new_state, new_token

    def invalidate(self, token: Optional[str]) -> None:
        """Hủy phiên phía máy chủ khi người dùng đăng xuất."""
        session_id = self._parse_token(token)
        if not session_id:
            return
        with self._lock:
            self._entries.pop(session_id, None)

    def _purge_expired_locked(self) -> None:
        now = time.time()
        expired = [
            session_id
            for session_id, (issued_at, _) in self._entries.items()
            if now - issued_at > self.ttl_seconds
        ]
        for session_id in expired:
            del self._entries[session_id]

    def active_session_count(self) -> int:
        with self._lock:
            self._purge_expired_locked()
            return len(self._entries)
