"""Kiểm thử hồi quy cho lỗ hổng path traversal khi phục vụ SPA."""

import os

from src.core.static_files import resolve_file_under


def _make_dist(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return dist


def test_serves_file_inside_dist(tmp_path):
    dist = _make_dist(tmp_path)
    resolved = resolve_file_under(str(dist), "assets/app.js")
    assert resolved == os.path.realpath(dist / "assets" / "app.js")


def test_blocks_parent_traversal(tmp_path):
    dist = _make_dist(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")

    assert resolve_file_under(str(dist), "../secret.txt") is None
    assert resolve_file_under(str(dist), "assets/../../secret.txt") is None


def test_blocks_absolute_path_override(tmp_path):
    dist = _make_dist(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")

    assert resolve_file_under(str(dist), str(secret)) is None
    assert resolve_file_under(str(dist), "/etc/passwd") is None


def test_blocks_sibling_prefix_escape(tmp_path):
    dist = _make_dist(tmp_path)
    sibling = tmp_path / "dist-leak"
    sibling.mkdir()
    (sibling / "leak.txt").write_text("leak", encoding="utf-8")

    assert resolve_file_under(str(dist), "../dist-leak/leak.txt") is None


def test_returns_none_for_missing_or_directory(tmp_path):
    dist = _make_dist(tmp_path)
    assert resolve_file_under(str(dist), "missing.html") is None
    assert resolve_file_under(str(dist), "") is None
