"""Bộ kiểm thử cho bộ phát hiện từ mơ hồ và gợi ý SMART."""

from src.analyzers.ambiguity_detector import AmbiguityDetector
from src.core.models import RequirementDTO
from src.utils.lexicon import NLPLexiconManager


def test_lexicon_singleton():
    lex1 = NLPLexiconManager()
    lex2 = NLPLexiconManager()
    assert lex1 is lex2


def test_detect_vague_terms():
    detector = AmbiguityDetector()
    text = "Giao diện phải cực kỳ thân thiện, dễ sử dụng và chạy thật nhanh."
    vague = detector.scan_ambiguous_terms(text, lang="vi")
    assert any("thân thiện" in t for t in vague)
    assert any("dễ sử dụng" in t for t in vague)
    assert any("nhanh" in t for t in vague)

    text_en = "The application must be fast and user-friendly."
    vague_en = detector.scan_ambiguous_terms(text_en, lang="en")
    assert "fast" in vague_en
    assert "user-friendly" in vague_en


def test_detect_missing_metric_in_nfr():
    detector = AmbiguityDetector()

    # NFR không có số liệu
    req_vague = RequirementDTO(
        req_id="REQ-01",
        raw_text="Hệ thống phải phản hồi thật nhanh.",
        req_type="NFR",
        nfr_category="Performance"
    )
    analyzed = detector.analyze(req_vague, lang="vi")
    assert analyzed.missing_metric is True
    assert analyzed.is_ambiguous is True
    assert analyzed.smart_rewrite != analyzed.raw_text

    # NFR đã có số liệu định lượng chuẩn
    req_clear = RequirementDTO(
        req_id="REQ-02",
        raw_text="Thời gian phản hồi phải dưới 1.5 giây khi có 1000 người dùng.",
        req_type="NFR",
        nfr_category="Performance"
    )
    analyzed_clear = detector.analyze(req_clear, lang="vi")
    assert analyzed_clear.missing_metric is False
