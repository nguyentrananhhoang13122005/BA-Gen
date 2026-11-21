"""Tiện ích phục vụ tệp tĩnh an toàn, chống path traversal."""

import os
from typing import Optional


def is_unsafe_relative_path(relative_path: str) -> bool:
    """Phát hiện đường dẫn tuyệt đối hoặc chứa thành phần '..'."""
    normalized = (relative_path or "").replace("\\", "/")
    if normalized.startswith("/"):
        return True
    return any(part == ".." for part in normalized.split("/"))


def resolve_file_under(base_dir: str, relative_path: str) -> Optional[str]:
    """Trả về đường dẫn thực của tệp nằm trong base_dir, hoặc None.

    Chặn cả đường dẫn tương đối chứa '..' lẫn đường dẫn tuyệt đối do client
    gửi lên, đồng thời resolve symlink để không phục vụ tệp ngoài thư mục.
    """
    if is_unsafe_relative_path(relative_path):
        return None

    base = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base, relative_path or ""))
    try:
        if os.path.commonpath([base, candidate]) != base:
            return None
    except ValueError:
        return None
    if not os.path.isfile(candidate):
        return None
    return candidate
