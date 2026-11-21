"""Bộ kiểm thử cho các chiến lược phân loại FR/NFR (Baseline, ML, Hybrid, Benchmark, LLM Mock)."""

from unittest.mock import MagicMock
from src.classifiers.evaluate_benchmark import BenchmarkEvaluator
from src.classifiers.hybrid_classifier import HybridClassifierStrategy
from src.classifiers.keyword_baseline import KeywordBaselineClassifier
from src.classifiers.llm_classifier import LLMClassifierStrategy
from src.classifiers.llm_client import MultiLLMClient
from src.classifiers.ml_classifier import OfflineMLClassifierStrategy
from src.core.database import DatabaseManager
from src.core.models import RequirementDTO


def test_keyword_baseline():
    classifier = KeywordBaselineClassifier()
    sentences = [
        "Người dùng có thể đăng nhập tài khoản.",
        "Thời gian phản hồi tìm kiếm phải dưới 500 ms.",
        "Mật khẩu phải được mã hóa bằng bcrypt an toàn."
    ]
    results = classifier.classify(sentences)
    assert len(results) == 3
    assert results[0].req_type == "FR"
    assert results[1].req_type == "NFR"
    assert results[1].nfr_category == "Performance"
    assert results[2].req_type == "NFR"
    assert results[2].nfr_category == "Security"


def test_offline_ml_classifier():
    classifier = OfflineMLClassifierStrategy()
    sentences = [
        "Khách hàng có thể tìm kiếm sản phẩm theo tên và danh mục.",
        "Hệ thống phải đảm bảo thời gian tải trang dưới 2 giây khi có 1000 người dùng."
    ]
    results = classifier.classify(sentences)
    assert len(results) == 2
    assert results[0].req_type == "FR"
    assert results[1].req_type == "NFR"
    assert 0.0 <= results[0].confidence <= 1.0
    assert 0.0 <= results[1].confidence <= 1.0


def test_hybrid_classifier_offline_fallback():
    db = DatabaseManager(":memory:")
    hybrid = HybridClassifierStrategy(db_manager=db)
    sentences = [
        "Người dùng có thể thêm mặt hàng vào giỏ hàng.",
        "Hệ thống mã hóa dữ liệu với TLS 1.3."
    ]
    results = hybrid.classify(sentences)
    assert len(results) == 2
    assert results[0].req_type in ["FR", "NFR"]


def test_benchmark_evaluator():
    evaluator = BenchmarkEvaluator()
    kw_metrics = evaluator.evaluate_keyword_baseline()
    assert "accuracy" in kw_metrics
    assert "macro_f1" in kw_metrics
    assert kw_metrics["accuracy"] > 0.50

    ml_metrics = evaluator.evaluate_offline_ml_kfold(n_splits=2)
    assert "accuracy" in ml_metrics
    assert ml_metrics["accuracy"] > 0.60


def test_llm_classifier_with_mock():
    mock_client = MagicMock(spec=MultiLLMClient)
    mock_client.is_configured.return_value = True
    mock_client.chat_completion.return_value = """
    {
      "batch_results": [
        {
          "index": 1,
          "req_type": "FR",
          "nfr_category": null,
          "confidence": 0.98,
          "reasoning": "Tính năng đăng nhập"
        }
      ]
    }
    """
    strategy = LLMClassifierStrategy(llm_client=mock_client)
    results = strategy.classify(["Khách hàng có thể đăng nhập bằng email."])
    assert len(results) == 1
    assert results[0].req_type == "FR"
    assert results[0].confidence == 0.98


def _build_hybrid_with_ml_confidences(confidences):
    """Tạo HybridClassifier với ML giả lập độ tin cậy cho từng câu."""
    db = DatabaseManager(":memory:")
    llm_client = MagicMock(spec=MultiLLMClient)
    llm_client.is_configured.return_value = True
    llm_client.provider = "test-provider"
    llm_client.model_name = "test-model"

    hybrid = HybridClassifierStrategy(db_manager=db, llm_client=llm_client)

    def fake_ml_classify(texts, lang="vi"):
        return [
            RequirementDTO(
                req_id=f"REQ-{i + 1:02d}",
                raw_text=text,
                req_type="FR" if confidence >= 0.5 else "NFR",
                nfr_category=None if confidence >= 0.5 else "Performance",
                confidence=confidence,
            )
            for i, (text, confidence) in enumerate(zip(texts, confidences))
        ]

    hybrid.ml_classifier.classify = MagicMock(side_effect=fake_ml_classify)
    return hybrid


def test_hybrid_llm_failure_keeps_all_sentences_aligned():
    """1 câu confident + 1 câu uncertain + LLM lỗi: phải giữ đủ 2 câu đúng thứ tự."""
    sentences = [
        "Người dùng có thể thêm sản phẩm vào giỏ hàng.",
        "Hệ thống phải phản hồi trong vòng 1 giây.",
    ]
    hybrid = _build_hybrid_with_ml_confidences([0.95, 0.10])
    hybrid.llm_classifier.classify = MagicMock(side_effect=RuntimeError("mất kết nối"))

    results = hybrid.classify(sentences)

    assert len(results) == 2
    assert all(result is not None for result in results)
    assert [r.raw_text for r in results] == sentences
    assert [r.req_id for r in results] == ["REQ-01", "REQ-02"]
    assert results[0].req_type == "FR"
    assert results[1].req_type == "NFR"


def test_hybrid_llm_short_response_falls_back_per_sentence():
    """LLM trả thiếu kết quả: câu còn lại phải dùng kết quả ML, không bị mất."""
    sentences = [
        "Người dùng có thể đăng xuất khỏi hệ thống.",
        "Hệ thống phải chịu được 1000 người dùng đồng thời.",
        "Dữ liệu phải được sao lưu hằng ngày.",
    ]
    hybrid = _build_hybrid_with_ml_confidences([0.95, 0.20, 0.15])
    hybrid.llm_classifier.classify = MagicMock(return_value=[
        RequirementDTO(
            req_id="ignored",
            raw_text=sentences[1],
            req_type="NFR",
            nfr_category="Security",
            confidence=0.90,
        )
    ])

    results = hybrid.classify(sentences)

    assert len(results) == 3
    assert all(result is not None for result in results)
    assert [r.raw_text for r in results] == sentences
    assert [r.req_id for r in results] == ["REQ-01", "REQ-02", "REQ-03"]
    assert len({r.req_id for r in results}) == 3
    # Câu 1 do ML xử lý, câu 2 do LLM trả về, câu 3 fallback về ML
    assert results[0].nfr_category is None
    assert results[1].nfr_category == "Security"
    assert results[2].nfr_category == "Performance"
