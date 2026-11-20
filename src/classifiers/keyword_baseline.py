"""Bộ phân loại FR/NFR Baseline dựa trên quy tắc từ khóa (Keyword-based).

Được sử dụng làm Baseline 1 để so sánh thực nghiệm trong báo cáo đánh giá benchmark.
"""

import re
from typing import List
from src.classifiers.base import IClassifierStrategy
from src.core.models import RequirementDTO

NFR_KEYWORDS = {
    "Performance": [
        "thời gian phản hồi", "response time", "giây", "phút", "ms", "latency",
        "throughput", "tải", "load", "tốc độ", "concurrent", "rps", "tps"
    ],
    "Security": [
        "bảo mật", "mã hóa", "security", "encrypt", "tls", "ssl", "bcrypt",
        "xác thực", "authentication", "quyền", "permission", "authorization",
        "session", "mật khẩu", "password", "token"
    ],
    "Usability": [
        "khả dụng", "tiếp cận", "accessibility", "wcag", "giao diện",
        "thân thiện", "dễ sử dụng", "user-friendly", "trực quan", "ux", "ui"
    ],
    "Reliability": [
        "sẵn sàng", "availability", "99.9%", "uptime", "downtime", "sao lưu",
        "backup", "khôi phục", "recovery", "mttr", "mttf", "chịu lỗi"
    ],
    "Maintainability": [
        "bảo trì", "mã nguồn", "source code", "module", "tài liệu",
        "maintainability", "refactor", "kiến trúc", "documentation", "clean code"
    ],
    "Portability": [
        "khả chuyển", "portability", "docker", "container", "nền tảng",
        "ios", "android", "cloud", "aws", "azure", "gcp", "cross-platform"
    ]
}


class KeywordBaselineClassifier(IClassifierStrategy):
    """Phân loại FR/NFR bằng so khớp từ khóa đơn giản."""

    def classify(self, sentences: List[str], lang: str = "vi") -> List[RequirementDTO]:
        results: List[RequirementDTO] = []

        for idx, sentence in enumerate(sentences, start=1):
            req_id = f"REQ-{idx:02d}"
            text_lower = sentence.lower()

            matched_category = None
            is_nfr = False

            # Quét các từ khóa NFR theo từng nhóm ISO 25010
            for cat, kws in NFR_KEYWORDS.items():
                for kw in kws:
                    if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                        matched_category = cat
                        is_nfr = True
                        break
                if is_nfr:
                    break

            if is_nfr:
                results.append(RequirementDTO(
                    req_id=req_id,
                    raw_text=sentence,
                    req_type="NFR",
                    nfr_category=matched_category,
                    confidence=0.70
                ))
            else:
                results.append(RequirementDTO(
                    req_id=req_id,
                    raw_text=sentence,
                    req_type="FR",
                    nfr_category=None,
                    confidence=0.75
                ))

        return results
