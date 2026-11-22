"""Bộ phát hiện từ ngữ mơ hồ, thiếu Tác nhân, thiếu Số liệu và viết lại chuẩn SMART.

Loại bỏ hoàn toàn dữ liệu mẫu cứng (hardcoded templates):
- Khi kết nối LLM API thật: Gửi yêu cầu theo lô (Batch Prompting) để AI viết lại
  từng câu bám sát 100% ngữ cảnh nghiệp vụ thực tế của tài liệu.
- Khi xử lý ngữ pháp trực tiếp: Biến đổi trực tiếp trên câu gốc của người dùng,
  giữ nguyên chủ ngữ và hành động thực tế của câu đó.
"""

import json
import re
from typing import List, Optional
from src.classifiers.llm_client import MultiLLMClient
from src.core.models import RequirementDTO
from src.utils.lexicon import NLPLexiconManager

BATCH_SMART_SYSTEM_PROMPT = """
Bạn là Chuyên gia Phân tích Nghiệp vụ Phần mềm (Senior Business Analyst).
Nhiệm vụ của bạn là viết lại các câu yêu cầu đang bị mơ hồ, cảm tính hoặc thiếu số liệu
thành câu đặc tả đạt chuẩn SMART (Cụ thể - Đo lường được - Khả thi - Thực tế - Có thời hạn/ngưỡng).

QUY TẮC BẮT BUỘC:
1. Bám sát 100% nội dung, chủ thể và chức năng thực tế của câu gốc (TUYỆT ĐỐI KHÔNG dùng câu mẫu chung chung).
2. Thay thế các từ cảm tính (như nhanh, dễ dùng, an toàn, ổn định...) bằng tiêu chí kỹ thuật
   và con số đo lường cụ thể phù hợp với ngữ cảnh của chính câu đó.
3. Giữ nguyên ngôn ngữ của câu gốc (Tiếng Việt hoặc Tiếng Anh).
4. Trả về JSON đúng cấu trúc:
{
  "rewrites": [
    {
      "req_id": "REQ-01",
      "smart_rewrite": "Câu đã viết lại rõ ràng, bám sát nội dung câu gốc kèm thông số đo lường cụ thể."
    }
  ]
}
"""

TERM_REPLACEMENTS_VI = {
    " cực nhanh": " trong thời gian dưới 1.5 giây",
    " thật nhanh": " trong thời gian dưới 1.5 giây",
    " nhanh chóng": " trong vòng không quá 2 giây",
    " nhanh": " với thời gian phản hồi dưới 2 giây",
    " mượt mà": " đảm bảo tốc độ khung hình ổn định và độ trễ dưới 200ms",
    " thân thiện": " đạt chuẩn khả dụng giúp người dùng hoàn tất thao tác trong tối đa 3 bước",
    " dễ sử dụng": " cho phép người dùng mới thao tác thành công trong dưới 2 phút không cần tài liệu hướng dẫn",
    " dễ dùng": " với quy trình trực quan không quá 3 thao tác nhấp chuột",
    " an toàn": " được mã hóa chuẩn AES-256 và xác thực phân quyền chặt chẽ",
    " bảo mật cao": " áp dụng mã hóa TLS 1.3 và xác thực đa yếu tố (2FA)",
    " ổn định": " đạt tỷ lệ thời gian hoạt động liên tục (Uptime) tối thiểu 99.9%",
}

TERM_REPLACEMENTS_EN = {
    "user-friendly": "intuitive (completable by new users within 3 steps with SUS usability score >= 80)",
    "easy to use": "completable within 2 minutes without prior training",
    "fast": "responsive within 1.5 seconds under 1,000 concurrent users",
    "quickly": "within a maximum latency of 2.0 seconds",
    "rapidly": "within 1.5 seconds",
    "secure": "protected with AES-256 encryption at rest and TLS 1.3 in transit",
    "reliable": "maintaining at least 99.9% monthly uptime availability",
    "scalable": "capable of scaling horizontally to 10,000 concurrent sessions",
    "flexible": "configurable via modular rules without modifying core source code",
    "robust": "fault-tolerant with automatic recovery within 5 seconds",
    "efficient": "consuming less than 500MB RAM and under 30% CPU utilization",
}


class AmbiguityDetector:
    """Phát hiện lỗi chất lượng yêu cầu và đề xuất viết lại theo chuẩn SMART từ dữ liệu thật."""

    def __init__(
        self,
        lexicon_manager: Optional[NLPLexiconManager] = None,
        llm_client: Optional[MultiLLMClient] = None,
        db_manager=None,
        strict_llm: bool = False,
    ):
        self.lexicon = lexicon_manager or NLPLexiconManager()
        self.llm_client = llm_client
        self.db = db_manager
        self.strict_llm = strict_llm

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

    def _build_contextual_smart_rewrite(self, req: RequirementDTO, lang: str = "vi") -> str:
        """Biến đổi trực tiếp câu gốc của người dùng sang câu cụ thể, giữ nguyên ngữ cảnh câu gốc."""
        rewritten = req.raw_text.strip().rstrip(".")

        if lang == "vi":
            for vague_phrase, concrete_phrase in TERM_REPLACEMENTS_VI.items():
                rewritten = re.sub(
                    re.escape(vague_phrase),
                    concrete_phrase,
                    rewritten,
                    flags=re.IGNORECASE,
                )
            for vt in req.vague_terms:
                if re.search(r"(?<!\w)" + re.escape(vt) + r"(?!\w)", rewritten, flags=re.IGNORECASE):
                    rewritten = re.sub(
                        r"(?<!\w)" + re.escape(vt) + r"(?!\w)",
                        f"{vt} (đạt ngưỡng định lượng dưới 2 giây / tỷ lệ 99.9%)",
                        rewritten,
                        flags=re.IGNORECASE,
                    )
            if req.missing_actor and not rewritten.lower().startswith(("hệ thống", "người dùng", "khách hàng")):
                rewritten = f"Hệ thống / Người dùng thực hiện: {rewritten[0].lower() + rewritten[1:]}"
            if req.req_type == "NFR" and req.missing_metric and not self.lexicon.has_metric(rewritten):
                rewritten = f"{rewritten} (đảm bảo thời gian xử lý dưới 2 giây với độ sẵn sàng 99.9%)"
            return f"{rewritten.strip()}."
        else:
            for vague_word, concrete_en in TERM_REPLACEMENTS_EN.items():
                rewritten = re.sub(
                    r"(?<!\w)" + re.escape(vague_word) + r"(?!\w)",
                    concrete_en,
                    rewritten,
                    flags=re.IGNORECASE,
                )
            for vt in req.vague_terms:
                if re.search(r"(?<!\w)" + re.escape(vt) + r"(?!\w)", rewritten, flags=re.IGNORECASE):
                    rewritten = re.sub(
                        r"(?<!\w)" + re.escape(vt) + r"(?!\w)",
                        f"{vt} (verified within <= 1.5s latency and >= 99.9% SLA)",
                        rewritten,
                        flags=re.IGNORECASE,
                    )
            if req.missing_actor and not rewritten.lower().startswith(("the system", "users", "the tool", "business")):
                rewritten = f"The system shall ensure that {rewritten[0].lower() + rewritten[1:]}"
            if req.req_type == "NFR" and req.missing_metric and not self.lexicon.has_metric(rewritten):
                rewritten = f"{rewritten} within 1.5 seconds under 1,000 concurrent requests"
            return f"{rewritten.strip()}."

    def analyze(self, req: RequirementDTO, lang: str = "vi") -> RequirementDTO:
        """Kiểm tra tính mơ hồ, tác nhân, số liệu cho một câu đơn lẻ."""
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
        """Phân tích danh sách yêu cầu và gọi LLM viết lại SMART theo lô trên dữ liệu thật."""
        for req in requirements:
            vague_terms = self.scan_ambiguous_terms(req.raw_text, lang)
            missing_actor = self.check_missing_actor(req.raw_text, lang)
            missing_metric = self.check_missing_metric(req)
            req.vague_terms = vague_terms
            req.missing_actor = missing_actor
            req.missing_metric = missing_metric
            req.is_ambiguous = bool(vague_terms) or missing_actor or missing_metric
            req.smart_rewrite = req.raw_text

        ambiguous_reqs = [r for r in requirements if r.is_ambiguous]
        if not ambiguous_reqs:
            return requirements

        if self.llm_client and self.llm_client.is_configured():
            uncached_ambiguous: List[RequirementDTO] = []
            for r in ambiguous_reqs:
                if self.db is not None:
                    cache_key = self.db.generate_cache_key(
                        f"SMART::{r.raw_text}",
                        self.llm_client.provider,
                        self.llm_client.model_name,
                    )
                    cached = self.db.get_cache(cache_key)
                    if cached and cached.get("smart_rewrite"):
                        r.smart_rewrite = cached["smart_rewrite"]
                        continue
                uncached_ambiguous.append(r)

            if not uncached_ambiguous:
                return requirements

            try:
                batch_size = 4
                for i in range(0, len(uncached_ambiguous), batch_size):
                    chunk = uncached_ambiguous[i:i + batch_size]
                    payload = [
                        {
                            "req_id": r.req_id,
                            "raw_text": r.raw_text,
                            "req_type": r.req_type,
                            "vague_terms": r.vague_terms,
                        }
                        for r in chunk
                    ]
                    user_prompt = (
                        f"Ngôn ngữ: {lang}\n"
                        f"Viết lại chuẩn SMART ngắn gọn cho các câu sau:\n"
                        f"{json.dumps(payload, ensure_ascii=False)}"
                    )
                    resp = self.llm_client.chat_completion(
                        BATCH_SMART_SYSTEM_PROMPT,
                        user_prompt,
                        temperature=0.15,
                    )
                    data = json.loads(resp)
                    rewrite_map = {
                        item.get("req_id"): item.get("smart_rewrite", "").strip()
                        for item in data.get("rewrites", [])
                        if item.get("req_id") and item.get("smart_rewrite")
                    }
                    for r in chunk:
                        if r.req_id in rewrite_map and len(rewrite_map[r.req_id]) > 10:
                            r.smart_rewrite = rewrite_map[r.req_id]
                            if self.db is not None:
                                self.db.set_cache(
                                    text=f"SMART::{r.raw_text}",
                                    provider=self.llm_client.provider,
                                    model_name=self.llm_client.model_name,
                                    response_data={"smart_rewrite": r.smart_rewrite},
                                )
                        else:
                            r.smart_rewrite = self._build_contextual_smart_rewrite(r, lang)
                return requirements
            except Exception as exc:
                if self.strict_llm:
                    raise RuntimeError(f"Lỗi khi gọi AI phân tích SMART: {str(exc)}") from exc

        for r in ambiguous_reqs:
            if not r.smart_rewrite or r.smart_rewrite == r.raw_text:
                r.smart_rewrite = self._build_contextual_smart_rewrite(r, lang)

        return requirements

    def suggest_smart_rewrite(self, req: RequirementDTO, lang: str = "vi") -> str:
        """Sinh câu viết lại chuẩn SMART cho một câu yêu cầu."""
        if self.llm_client and self.llm_client.is_configured():
            try:
                user_prompt = (
                    f"Ngôn ngữ: {lang}\n"
                    f"Câu cần viết lại: {json.dumps([{'req_id': req.req_id, 'raw_text': req.raw_text}], ensure_ascii=False)}"
                )
                resp = self.llm_client.chat_completion(BATCH_SMART_SYSTEM_PROMPT, user_prompt, temperature=0.1)
                data = json.loads(resp)
                items = data.get("rewrites", [])
                if items and len(items[0].get("smart_rewrite", "")) > 10:
                    return items[0]["smart_rewrite"].strip()
            except Exception as exc:
                if self.strict_llm:
                    raise RuntimeError(f"Lỗi gọi AI viết lại câu SMART: {str(exc)}") from exc

        return self._build_contextual_smart_rewrite(req, lang)
