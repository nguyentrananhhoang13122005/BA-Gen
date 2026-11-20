"""Bộ phân loại FR/NFR sử dụng mô hình LLM với kỹ thuật Batch Prompting.

Gom 10-15 câu/lượt gọi API để tiết kiệm hạn mức token, tránh lỗi HTTP 429
và trả về đầu ra JSON có cấu trúc chặt chẽ.
"""

import json
from typing import List, Optional
from src.classifiers.base import IClassifierStrategy
from src.classifiers.llm_client import MultiLLMClient
from src.core.models import RequirementDTO

CLASSIFICATION_SYSTEM_PROMPT = """
Bạn là một Chuyên gia Phân tích Yêu cầu Phần mềm (Business Analyst / Requirements Engineer) giàu kinh nghiệm.
Nhiệm vụ của bạn là phân loại một danh sách các câu yêu cầu phần mềm thành:
1. 'FR' (Functional Requirement - Yêu cầu Chức năng: mô tả hệ thống LÀM GÌ, tính năng, hành vi người dùng).
2. 'NFR' (Non-Functional Requirement - Yêu cầu Phi chức năng: mô tả hệ thống PHẢI NHƯ THẾ NÀO, ràng buộc chất lượng).

Đối với mỗi câu NFR, bạn BẮT BUỘC phải gán nhãn phụ theo chuẩn ISO/IEC 25010 thuộc một trong các nhóm:
- 'Performance' (Hiệu năng: thời gian phản hồi, tải, dung lượng, băng thông)
- 'Security' (Bảo mật: mã hóa, phân quyền, xác thực, mật khẩu, phiên)
- 'Usability' (Khả dụng: giao diện, độ dễ dùng, khả năng tiếp cận WCAG)
- 'Reliability' (Độ tin cậy: sẵn sàng 99.9%, sao lưu, khôi phục, chịu lỗi)
- 'Maintainability' (Khả năng bảo trì: cấu trúc code, module, tài liệu hóa)
- 'Portability' (Khả chuyển: tương thích nền tảng, Docker, iOS, Android, Cloud)
Đối với câu FR, trường 'nfr_category' phải là null.

BẠN BẮT BUỘC PHẢI TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON NHƯ SAU:
{
  "batch_results": [
    {
      "index": 1,
      "req_type": "FR",
      "nfr_category": null,
      "confidence": 0.95,
      "reasoning": "Lý giải ngắn gọn"
    },
    {
      "index": 2,
      "req_type": "NFR",
      "nfr_category": "Performance",
      "confidence": 0.98,
      "reasoning": "Ràng buộc thời gian phản hồi"
    }
  ]
}
"""


class LLMClassifierStrategy(IClassifierStrategy):
    """Chiến lược phân loại FR/NFR sử dụng LLM theo lô (Batching)."""

    def __init__(self, llm_client: Optional[MultiLLMClient] = None, batch_size: int = 12):
        self.client = llm_client or MultiLLMClient()
        self.batch_size = batch_size

    def classify(self, sentences: List[str], lang: str = "vi") -> List[RequirementDTO]:
        results: List[RequirementDTO] = []
        if not sentences:
            return results

        total_sentences = len(sentences)

        for i in range(0, total_sentences, self.batch_size):
            chunk = sentences[i:i + self.batch_size]
            prompt_items = [
                {"index": idx + 1, "text": sentence}
                for idx, sentence in enumerate(chunk)
            ]
            items_json = json.dumps(prompt_items, ensure_ascii=False, indent=2)
            user_prompt = f"Ngôn ngữ tài liệu: {lang}\nDanh sách câu cần phân loại:\n{items_json}"

            raw_json = self.client.chat_completion(
                system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1
            )

            try:
                data = json.loads(raw_json)
                batch_items = data.get("batch_results", [])
                item_map = {item["index"]: item for item in batch_items}

                for idx, sentence in enumerate(chunk):
                    global_idx = i + idx + 1
                    req_id = f"REQ-{global_idx:02d}"
                    parsed_item = item_map.get(idx + 1, {})

                    req_type = parsed_item.get("req_type", "FR").upper()
                    if req_type not in ["FR", "NFR"]:
                        req_type = "FR"

                    nfr_cat = parsed_item.get("nfr_category") if req_type == "NFR" else None
                    conf = float(parsed_item.get("confidence", 0.90))

                    results.append(RequirementDTO(
                        req_id=req_id,
                        raw_text=sentence,
                        req_type=req_type,
                        nfr_category=nfr_cat,
                        confidence=conf
                    ))

            except Exception:
                for idx, sentence in enumerate(chunk):
                    global_idx = i + idx + 1
                    results.append(RequirementDTO(
                        req_id=f"REQ-{global_idx:02d}",
                        raw_text=sentence,
                        req_type="FR",
                        nfr_category=None,
                        confidence=0.70
                    ))

        return results
