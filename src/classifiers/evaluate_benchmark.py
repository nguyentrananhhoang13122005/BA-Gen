"""Module Đánh giá Kiểm chuẩn (Benchmark Evaluator) trên bộ 35 câu yêu cầu.

Đo lường các chỉ số định lượng: Accuracy, Precision, Recall, Macro F1-Score
và Ma trận Nhầm lẫn 2x2. Hỗ trợ Stratified K-Fold cho Offline ML.
"""

import json
import os
from typing import Dict, Any
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from src.classifiers.keyword_baseline import KeywordBaselineClassifier


class BenchmarkEvaluator:
    """Đánh giá và so sánh hiệu năng các mô hình phân loại trên tập kiểm chuẩn."""

    def __init__(self, benchmark_file: str = "data/benchmark_35_reqs.json"):
        if not os.path.isabs(benchmark_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            benchmark_file = os.path.join(base_dir, benchmark_file)

        self.benchmark_file = benchmark_file
        self.dataset = self._load_data()

    def _load_data(self):
        with open(self.benchmark_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def evaluate_keyword_baseline(self) -> Dict[str, Any]:
        """Đánh giá mô hình Baseline từ khóa."""
        texts = [item["text"] for item in self.dataset]
        y_true = [1 if item["type"] == "NFR" else 0 for item in self.dataset]

        classifier = KeywordBaselineClassifier()
        predictions = classifier.classify(texts)
        y_pred = [1 if req.req_type == "NFR" else 0 for req in predictions]

        return self._compute_metrics("Keyword Baseline", y_true, y_pred)

    def evaluate_offline_ml_kfold(self, n_splits: int = 5) -> Dict[str, Any]:
        """Đánh giá mô hình Offline LinearSVC bằng Stratified K-Fold để tránh rò rỉ dữ liệu."""
        texts = [item["text"] for item in self.dataset]
        y_true = [1 if item["type"] == "NFR" else 0 for item in self.dataset]

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.svm import LinearSVC

        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        y_preds = [0] * len(y_true)

        for train_idx, test_idx in skf.split(texts, y_true):
            X_train = [texts[i] for i in train_idx]
            y_train = [y_true[i] for i in train_idx]
            X_test = [texts[i] for i in test_idx]

            vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")
            X_train_vec = vec.fit_transform(X_train)
            X_test_vec = vec.transform(X_test)

            clf = LinearSVC(C=1.0, class_weight="balanced", random_state=42)
            clf.fit(X_train_vec, y_train)
            test_preds = clf.predict(X_test_vec)

            for idx, pred in zip(test_idx, test_preds):
                y_preds[idx] = int(pred)

        return self._compute_metrics("Offline LinearSVC (5-Fold CV)", y_true, y_preds)

    def evaluate_hybrid_classifier(self, hybrid_classifier) -> Dict[str, Any]:
        """Đánh giá mô hình lai ghép Hybrid Classifier."""
        texts = [item["text"] for item in self.dataset]
        y_true = [1 if item["type"] == "NFR" else 0 for item in self.dataset]

        predictions = hybrid_classifier.classify(texts)
        y_pred = [1 if req.req_type == "NFR" else 0 for req in predictions]

        return self._compute_metrics("Hybrid Classifier", y_true, y_pred)

    @staticmethod
    def _compute_metrics(model_name: str, y_true, y_pred) -> Dict[str, Any]:
        acc = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=0)
        macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
        cm = confusion_matrix(y_true, y_pred)

        return {
            "model_name": model_name,
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "macro_precision": round(macro_p, 4),
            "macro_recall": round(macro_r, 4),
            "fr_precision": round(precision[0], 4),
            "fr_recall": round(recall[0], 4),
            "fr_f1": round(f1[0], 4),
            "nfr_precision": round(precision[1], 4),
            "nfr_recall": round(recall[1], 4),
            "nfr_f1": round(f1[1], 4),
            "confusion_matrix": cm.tolist()
        }


if __name__ == "__main__":
    evaluator = BenchmarkEvaluator()
    print("--- 1. Baseline Từ khóa ---")
    print(json.dumps(evaluator.evaluate_keyword_baseline(), indent=2))
    print("\n--- 2. Offline LinearSVC (5-Fold CV) ---")
    print(json.dumps(evaluator.evaluate_offline_ml_kfold(), indent=2))
