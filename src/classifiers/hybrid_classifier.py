"""Bộ phân loại FR/NFR lai ghép (Hybrid) kết hợp Cache, Offline ML và Multi-LLM.

Tối ưu hóa chi phí API thông qua SQLite Cache, xử lý nhanh bằng LinearSVC
và chỉ gọi LLM đối với các câu có độ tin cậy thấp (< 75%), kèm cơ chế tự động
chuyển mạch dự phòng (Circuit-Breaker Fallback) khi mất mạng hoặc quá hạn mức.
"""

from typing import List, Optional
from src.classifiers.base import IClassifierStrategy
from src.classifiers.llm_classifier import LLMClassifierStrategy
from src.classifiers.llm_client import MultiLLMClient
from src.classifiers.ml_classifier import OfflineMLClassifierStrategy
from src.core.database import DatabaseManager
from src.core.models import RequirementDTO


class HybridClassifierStrategy(IClassifierStrategy):
    """Mô hình phân loại lai ghép 3 tầng: Cache -> Offline ML -> Multi-LLM + Fallback."""

    def __init__(
        self,
        llm_client: Optional[MultiLLMClient] = None,
        db_manager: Optional[DatabaseManager] = None,
        confidence_threshold: float = 0.75,
        force_llm_mode: bool = False,
        strict_llm: bool = False,
    ):
        self.llm_client = llm_client or MultiLLMClient()
        self.ml_classifier = OfflineMLClassifierStrategy()
        self.llm_classifier = LLMClassifierStrategy(llm_client=self.llm_client, strict_llm=strict_llm)
        self.db = db_manager or DatabaseManager()
        self.confidence_threshold = confidence_threshold
        self.force_llm_mode = force_llm_mode
        self.strict_llm = strict_llm

    def classify(self, sentences: List[str], lang: str = "vi") -> List[RequirementDTO]:
        if not sentences:
            return []

        results: List[RequirementDTO] = []
        sentences_to_evaluate: List[tuple[int, str]] = []  # (original_idx, text)

        # Tầng 1: Kiểm tra SQLite Cache qua mã băm SHA-256
        for idx, sentence in enumerate(sentences):
            cache_key = self.db.generate_cache_key(
                sentence, self.llm_client.provider, self.llm_client.model_name
            )
            cached_data = self.db.get_cache(cache_key)

            if cached_data:
                results.append(RequirementDTO(
                    req_id=f"REQ-{idx + 1:02d}",
                    raw_text=sentence,
                    req_type=cached_data.get("req_type", "FR"),
                    nfr_category=cached_data.get("nfr_category"),
                    confidence=float(cached_data.get("confidence", 0.95))
                ))
            else:
                results.append(None)  # Placeholder giữ đúng vị trí
                sentences_to_evaluate.append((idx, sentence))

        if not sentences_to_evaluate:
            return results

        # Tầng 2: Chạy mô hình Offline ML (LinearSVC) trên CPU
        uncached_texts = [text for _, text in sentences_to_evaluate]
        ml_predictions = self.ml_classifier.classify(uncached_texts, lang=lang)

        uncertain_indices: List[int] = []
        uncertain_sentences: List[str] = []
        ml_by_index = {}

        for (orig_idx, sentence), ml_pred in zip(sentences_to_evaluate, ml_predictions):
            ml_pred.req_id = f"REQ-{orig_idx + 1:02d}"
            ml_by_index[orig_idx] = ml_pred

            # Nếu bật ép buộc LLM hoặc độ tin cậy < ngưỡng -> đưa vào danh sách gọi LLM
            if self.force_llm_mode or ml_pred.confidence < self.confidence_threshold:
                uncertain_indices.append(orig_idx)
                uncertain_sentences.append(sentence)
            else:
                results[orig_idx] = ml_pred

        def keep_ml_fallback(indices: List[int]):
            """Giữ kết quả LinearSVC cho các câu LLM chưa trả về."""
            for idx in indices:
                if results[idx] is None:
                    results[idx] = ml_by_index[idx]

        # Tầng 3: Định tuyến các câu chưa chắc chắn sang LLM API
        if uncertain_sentences and self.llm_client.is_configured():
            try:
                llm_preds = self.llm_classifier.classify(uncertain_sentences, lang=lang)
                for orig_idx, sentence, llm_pred in zip(uncertain_indices, uncertain_sentences, llm_preds):
                    llm_pred.req_id = f"REQ-{orig_idx + 1:02d}"
                    results[orig_idx] = llm_pred

                    # Lưu vào SQLite Cache để tái sử dụng
                    self.db.set_cache(
                        text=sentence,
                        provider=self.llm_client.provider,
                        model_name=self.llm_client.model_name,
                        response_data={
                            "req_type": llm_pred.req_type,
                            "nfr_category": llm_pred.nfr_category,
                            "confidence": llm_pred.confidence
                        }
                    )
                # LLM có thể trả thiếu kết quả -> bù bằng kết quả ML theo đúng orig_idx
                keep_ml_fallback(uncertain_indices)
            except Exception as exc:
                if self.strict_llm:
                    raise RuntimeError(f"Lỗi kết nối API AI ({self.llm_client.provider}): {str(exc)}") from exc
                # Kích hoạt Circuit-Breaker: giữ kết quả của LinearSVC nếu LLM lỗi mạng/quota
                keep_ml_fallback(uncertain_indices)
        else:
            # Nếu không cấu hình LLM hoặc không có kết nối, dùng kết quả ML
            keep_ml_fallback(uncertain_indices)

        for idx, result in enumerate(results):
            if result is None:
                results[idx] = ml_by_index.get(idx) or RequirementDTO(
                    req_id=f"REQ-{idx + 1:02d}", raw_text=sentences[idx]
                )

        return results
