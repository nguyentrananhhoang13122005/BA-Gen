"""Bộ phát hiện từ ngữ mơ hồ, thiếu Tác nhân, thiếu Số liệu và gợi ý chuẩn SMART.

Đối chiếu với từ điển hơn 120 từ cảm tính song ngữ, phát hiện câu bị động
thiếu chủ thể và câu NFR thiếu tiêu chí định lượng đo lường được.
"""

import json
import re
from typing import List, Optional
from src.classifiers.llm_client import MultiLLMClient
from src.core.models import RequirementDTO
from src.utils.lexicon import NLPLexiconManager

SMART_OFFLINE_TEMPLATES_VI = {
    "Performance": "Hệ thống phải phản hồi kết quả trong vòng dưới 1.5 giây trong điều kiện tải 1000 người dùng đồng thời.",
    "Security": "Hệ thống phải mã hóa dữ liệu nhạy cảm bằng thuật toán AES-256 và truyền tải qua giao thức TLS 1.3.",
    "Usability": "Người dùng mới phải có thể hoàn tất quy trình trong vòng dưới 3 phút mà không cần hướng dẫn.",
    "Reliability": "Hệ thống phải duy trì thời gian hoạt động liên tục đạt tỷ lệ sẵn sàng ít nhất 99.9% mỗi tháng.",
    "Maintainability": (
        "Mã nguồn phải được tổ chức theo module độc lập và tài liệu hóa đầy đủ trong vòng 24 giờ sau phát hành."
    ),
    "Portability": "Ứng dụng phải hoạt động tương thích trên hệ điều hành iOS (từ phiên bản 15) và Android (từ phiên bản 11)."
}

SMART_OFFLINE_TEMPLATES_EN = {
    "Performance": "The system shall respond to user requests within 1.5 seconds under a load of 1,000 concurrent users.",
    "Security": "The application shall encrypt all sensitive data at rest using AES-256 and in transit using TLS 1.3.",
    "Usability": "New users shall be able to complete the primary workflow within 3 minutes without assistance.",
    "Reliability": "The system shall maintain an uptime availability of at least 99.9% on a monthly basis.",
    "Maintainability": "Source code shall be modularized with automated test coverage exceeding 85%.",
    "Portability": "The application shall run seamlessly on iOS 15+ and Android 11+ platforms."
}


class AmbiguityDetector:
    """Phát hiện lỗi chất lượng yêu cầu và đề xuất viết lại theo chuẩn SMART."""

    def __init__(self, lexicon_manager: Optional[NLPLexiconManager] = None, llm_client: Optional[MultiLLMClient] = None):
        self.lexicon = lexicon_manager or NLPLexiconManager()
        self.llm_client = llm_client

    def scan_ambiguous_terms(self, text: str, lang: str = "vi") -> List[str]:
        """Tìm tất cả các từ/cụm từ cảm tính mơ hồ xuất hiện trong câu."""
        terms = self.lexicon.get_ambiguous_terms(lang)
        text_lower = text.lower()
        found = []

        for term in terms:
            pattern = r"(?<!\w)" + re.escape(term) + r"(?!\w)"
            if re.search(pattern, text_lower):
                found.append(term)

        unique_found = []
        for t in sorted(found, key=len, reverse=True):
            if not any(t != other and t in other for other in unique_found):
                unique_found.append(t)

        return unique_found

    def check_missing_actor(self, text: str, lang: str = "vi") -> bool:
        """Kiểm tra câu có bị thiếu chủ thể / tác nhân hay không."""
        actors = self.lexicon.get_actors(lang)
        text_lower = text.lower()

        for actor in actors:
            if re.search(r"\b" + re.escape(actor) + r"\b", text_lower):
                return False

        if lang == "vi":
            words = text_lower.split()
            if words and words[0] in ["được", "cần", "phải"]:
                return True
        else:
            if re.search(r"\b(is|are|was|were|shall be|must be)\s+[a-z]+ed\b", text_lower):
                return True

        return True

    def check_missing_metric(self, req: RequirementDTO) -> bool:
        """Kiểm tra xem câu NFR có thiếu chỉ số định lượng hay không."""
        if req.req_type != "NFR":
            return False
        return not self.lexicon.has_metric(req.raw_text)

    def analyze(self, req: RequirementDTO, lang: str = "vi") -> RequirementDTO:
        """Kiểm tra toàn diện tính mơ hồ, tác nhân, số liệu và sinh gợi ý SMART."""
        vague_terms = self.scan_ambiguous_terms(req.raw_text, lang)
        missing_actor = self.check_missing_actor(req.raw_text, lang)
        missing_metric = self.check_missing_metric(req)

        is_ambiguous = bool(vague_terms) or missing_actor or missing_metric

        req.vague_terms = vague_terms
        req.missing_actor = missing_actor
        req.missing_metric = missing_metric
        req.is_ambiguous = is_ambiguous

        if is_ambiguous:
            req.smart_rewrite = self.suggest_smart_rewrite(req, lang)
        else:
            req.smart_rewrite = req.raw_text

        return req

    def analyze_batch(self, requirements: List[RequirementDTO], lang: str = "vi") -> List[RequirementDTO]:
        """Phân tích danh sách yêu cầu hàng loạt."""
        return [self.analyze(req, lang=lang) for req in requirements]

    def suggest_smart_rewrite(self, req: RequirementDTO, lang: str = "vi") -> str:
        """Sinh câu viết lại chuẩn SMART bằng mẫu ngoại tuyến hoặc LLM trực tuyến."""
        if self.llm_client and self.llm_client.is_configured():
            try:
                system_prompt = (
                    "Bạn là chuyên gia Kỹ thuật Yêu cầu phần mềm. Hãy viết lại câu yêu cầu bị mơ hồ/thiếu số liệu "
                    "thành một câu đơn duy nhất đạt chuẩn SMART. "
                    "Giữ nguyên ngôn ngữ và trả về JSON: {\"smart_rewrite\": \"...\"}"
                )
                user_prompt = (
                    f"Câu gốc: {req.raw_text}\n"
                    f"Loại yêu cầu: {req.req_type} ({req.nfr_category or ''})\n"
                    f"Lỗi: Từ mơ hồ ({', '.join(req.vague_terms)}), "
                    f"Thiếu tác nhân: {req.missing_actor}, Thiếu số liệu: {req.missing_metric}"
                )
                resp = self.llm_client.chat_completion(system_prompt, user_prompt, temperature=0.1)
                data = json.loads(resp)
                if "smart_rewrite" in data and len(data["smart_rewrite"]) > 10:
                    return data["smart_rewrite"].strip()
            except Exception:
                pass

        cat = req.nfr_category or "Performance"
        templates = SMART_OFFLINE_TEMPLATES_VI if lang == "vi" else SMART_OFFLINE_TEMPLATES_EN
        default_smart = templates.get(cat, templates["Performance"])

        if req.req_type == "FR":
            actor = "Người dùng" if lang == "vi" else "The user"
            clean_text = req.raw_text
            for vt in req.vague_terms:
                clean_text = re.sub(r"(?i)\b" + re.escape(vt) + r"\b", "", clean_text)
            clean_text = " ".join(clean_text.split())
            if req.missing_actor:
                return f"{actor} có thể {clean_text[0].lower() + clean_text[1:] if lang == 'vi' else clean_text}."
            return clean_text

        return default_smart
