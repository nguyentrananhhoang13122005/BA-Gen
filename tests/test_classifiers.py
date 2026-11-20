"""Bộ kiểm thử cho các chiến lược phân loại FR/NFR (Baseline, ML, Hybrid, Benchmark, LLM Mock)."""

from unittest.mock import MagicMock
from src.classifiers.evaluate_benchmark import BenchmarkEvaluator
from src.classifiers.hybrid_classifier import HybridClassifierStrategy
from src.classifiers.keyword_baseline import KeywordBaselineClassifier
from src.classifiers.llm_classifier import LLMClassifierStrategy
from src.classifiers.llm_client import MultiLLMClient
from src.classifiers.ml_classifier import OfflineMLClassifierStrategy
from src.core.database import DatabaseManager


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
