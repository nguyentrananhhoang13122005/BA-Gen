"""Bộ kiểm thử cho RequirementSegmenter."""

from src.parsers.segmenter import RequirementSegmenter


def test_detect_language():
    assert RequirementSegmenter.detect_language("Hệ thống phải phản hồi nhanh.") == "vi"
    assert RequirementSegmenter.detect_language("The system must respond within 2 seconds.") == "en"


def test_clean_bullet_points():
    text = """
    • 1. Tính năng đăng nhập
    - a) Cho phép đặt lại mật khẩu
    * 3) Gửi email xác thực
    """
    cleaned = RequirementSegmenter.clean_bullet_points(text)
    assert "•" not in cleaned
    assert "1." not in cleaned
    assert "Tính năng đăng nhập" in cleaned


def test_segmenter_protects_abbreviations_and_decimals():
    text = (
        "Thời gian phản hồi tìm kiếm phải dưới 1.5 giây khi đạt tỷ lệ 99.9% uptime. "
        "Người dùng có thể tra cứu thông tin (VD. số điện thoại hoặc mã đơn hàng) tức thì."
    )
    sentences, lang = RequirementSegmenter.segment(text)
    assert lang == "vi"
    assert len(sentences) >= 2

    # Kiểm tra số thập phân không bị cắt đứt
    combined = " ".join(sentences)
    assert "1.5" in combined
    assert "99.9%" in combined
    assert "VD." in combined


def test_segmenter_filters_short_sentences():
    # Câu < 4 từ phải bị loại bỏ
    text = "Xin chào. OK. Hệ thống cho phép khách hàng thanh toán qua ví điện tử."
    sentences, _ = RequirementSegmenter.segment(text)
    assert len(sentences) == 1
    assert "thanh toán qua ví điện tử" in sentences[0]
