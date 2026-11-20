"""Bộ phân loại FR/NFR ngoại tuyến sử dụng học máy thống kê TF-IDF + LinearSVC.

Hoạt động hoàn toàn trên CPU, phản hồi trong vài chục mili-giây và đóng vai trò
lớp dự phòng (fallback) đáng tin cậy khi LLM gặp sự cố hoặc mất kết nối mạng.
"""

import json
import math
import os
import re
from typing import List, Optional
from src.classifiers.base import IClassifierStrategy
from src.classifiers.keyword_baseline import NFR_KEYWORDS
from src.core.models import RequirementDTO


class OfflineMLClassifierStrategy(IClassifierStrategy):
    """Mô hình phân loại nhẹ scikit-learn (TF-IDF + LinearSVC)."""

    def __init__(self, benchmark_data_path: Optional[str] = None):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents=None,
            token_pattern=r"(?u)\b\w+\b"
        )
        self.classifier = LinearSVC(C=1.0, class_weight="balanced", random_state=42)
        self._is_fitted = False

        if benchmark_data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            benchmark_data_path = os.path.join(base_dir, "data", "benchmark_35_reqs.json")

        self.benchmark_data_path = benchmark_data_path
        self._train_default_model()

    def _train_default_model(self):
        """Huấn luyện nhanh mô hình trên 35 câu kiểm chuẩn có sẵn."""
        if not os.path.exists(self.benchmark_data_path):
            return

        with open(self.benchmark_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        texts = [item["text"] for item in data]
        # Nhãn: 1 cho NFR, 0 cho FR
        labels = [1 if item["type"] == "NFR" else 0 for item in data]

        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)
        self._is_fitted = True

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Hàm sigmoid chuyển đổi điểm biên LinearSVC sang xác suất 0.0 - 1.0."""
        return 1.0 / (1.0 + math.exp(-x))

    def _determine_nfr_category(self, text: str) -> str:
        """Gán nhãn phụ NFR chuẩn ISO 25010 theo từ khóa khi chạy ngoại tuyến."""
        text_lower = text.lower()
        for cat, kws in NFR_KEYWORDS.items():
            for kw in kws:
                if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                    return cat
        return "Performance"  # Nhóm NFR mặc định

    def classify(self, sentences: List[str], lang: str = "vi") -> List[RequirementDTO]:
        results: List[RequirementDTO] = []
        if not sentences:
            return results

        if not self._is_fitted:
            # Nếu chưa fit, fallback tạm sang Keyword Baseline
            from src.classifiers.keyword_baseline import KeywordBaselineClassifier
            return KeywordBaselineClassifier().classify(sentences, lang)

        X = self.vectorizer.transform(sentences)
        decisions = self.classifier.decision_function(X)

        for idx, (sentence, score) in enumerate(zip(sentences, decisions), start=1):
            req_id = f"REQ-{idx:02d}"
            prob_nfr = self._sigmoid(score)

            if prob_nfr >= 0.50:
                req_type = "NFR"
                category = self._determine_nfr_category(sentence)
                confidence = round(prob_nfr, 2)
            else:
                req_type = "FR"
                category = None
                confidence = round(1.0 - prob_nfr, 2)

            results.append(RequirementDTO(
                req_id=req_id,
                raw_text=sentence,
                req_type=req_type,
                nfr_category=category,
                confidence=confidence
            ))

        return results
