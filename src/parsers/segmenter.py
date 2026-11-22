"""Bộ tiền xử lý, nhận diện ngôn ngữ và tách câu yêu cầu song ngữ.

Bảo vệ số thập phân (99.9%), các chữ viết tắt (VD., e.g., TP.) và cắt bỏ
ký hiệu gạch đầu dòng để tách thành các câu yêu cầu nguyên tử.
"""

import re
import unicodedata
from typing import List, Tuple

# Ký tự có dấu đặc trưng của tiếng Việt
VIETNAMESE_DIACRITICS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")

# Danh sách từ viết tắt cần bảo vệ tránh bị ngắt câu sai
ABBREVIATIONS = [
    r"\be\.g\.", r"\bi\.e\.", r"\bvd\.", r"\btp\.", r"\bts\.",
    r"\bth\.", r"\bvs\.", r"\bno\.", r"\bapprox\.", r"\bdr\.",
    r"\bmr\.", r"\bms\.", r"\bprof\."
]


class RequirementSegmenter:
    """Tách câu yêu cầu song ngữ Anh - Việt và nhận diện ngôn ngữ."""

    @staticmethod
    def extract_system_title(raw_text: str, fallback_title: str = "Hệ thống Phần mềm") -> str:
        """Trích xuất tên chính xác của hệ thống phần mềm từ nội dung tài liệu BRD/SRS.

        Tuyệt đối ưu tiên lấy tên phần mềm/hệ thống được nêu trong tài liệu
        (VD: 'Hệ thống Quản lý Nhân sự (HRM)', 'Hệ thống Quản lý Kho hàng (WMS)')
        thay vì lấy tên file hoặc tiêu đề tài liệu.
        """
        if not raw_text or not raw_text.strip():
            return fallback_title

        normalized = unicodedata.normalize("NFC", raw_text)

        # 1. Tìm dòng tiêu đề hoặc câu định nghĩa 'HỆ THỐNG QUẢN LÝ ... (XXX)' hoặc 'Hệ thống ... (XXX) được xây dựng'
        patterns = [
            r"(Hệ\s+thống\s+Quản\s+lý\s+[^\n.;|—]{2,55}?\([A-Z0-9&\-]{2,15}\))",
            r"(Hệ\s+thống\s+[^\n.;|—]{3,55}?\([A-Z0-9&\-]{2,15}\))\s+được\s+xây\s+dựng",
            r"TÀI\s+LIỆU\s+PHÂN\s+TÍCH\s+NGHIỆP\s+VỤ[^\n]*?\n+\s*(HỆ\s+THỐNG\s+[^\n|—]{4,65})",
            r"(?:Tên\s+hệ\s+thống|Tên\s+phần\s+mềm|Dự\s+án)\s*:\s*(Hệ\s+thống\s+[^\n.;|]{3,65})",
            r"(Requirements\s+Analysis\s+Assistant(?:\s+Using\s+Natural\s+Language\s+Processing)?)",
        ]
        for pat in patterns:
            match = re.search(pat, normalized, flags=re.IGNORECASE)
            if match:
                candidate = " ".join(match.group(1).split()).strip(" —-|:")
                # Chuẩn hóa viết hoa kiểu Title Case nếu toàn bộ đang IN HOA
                if candidate.isupper():
                    # Giữ nguyên chữ viết tắt trong ngoặc đơn (VD: (HRM), (WMS))
                    def _title_preserve_acronym(m):
                        return m.group(0).upper()

                    titled = candidate.title()
                    titled = re.sub(r"\([A-Za-z0-9&\-]+\)", _title_preserve_acronym, titled)
                    titled = re.sub(r"\bHệ Thống\b", "Hệ thống", titled)
                    titled = re.sub(r"\bQuản Lý\b", "Quản lý", titled)
                    return titled
                return candidate

        # 2. Nếu fallback_title là tên file (VD: Tai_lieu_BA_Quan_ly_Nhan_vien.docx), làm sạch tiền tố tài liệu
        cleaned = re.sub(r"\.(docx|txt|md|pdf)$", "", fallback_title or "", flags=re.IGNORECASE)
        cleaned = cleaned.replace("_", " ").strip()
        cleaned = re.sub(
            r"^(Tài\s+liệu\s+BA|Tai\s+lieu\s+BA|Tài\s+liệu\s+SRS|BRD|SRS|Topic\s+\d+)\s*[—\-:]?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned and not re.match(r"^(Hệ\s+thống|System|Phần\s+mềm)\b", cleaned, flags=re.IGNORECASE):
            if re.match(r"^(Quản\s+lý|Quan\s+ly)\b", cleaned, flags=re.IGNORECASE):
                cleaned = f"Hệ thống {cleaned}"
        return cleaned or "Hệ thống Phần mềm"

    @staticmethod
    def detect_language(text: str) -> str:
        """Nhận diện ngôn ngữ 'vi' hoặc 'en' dựa trên dấu thanh tiếng Việt."""
        normalized = unicodedata.normalize("NFC", text.lower())
        vi_char_count = sum(1 for char in normalized if char in VIETNAMESE_DIACRITICS)
        words = normalized.split()
        total_words = len(words)

        if total_words == 0:
            return "vi"

        # Nếu có từ 2 ký tự tiếng Việt có dấu trở lên, kết luận là tiếng Việt
        if vi_char_count >= 2:
            return "vi"

        # Kiểm tra một số từ chức năng phổ biến tiếng Việt không dấu
        vi_common_words = {"va", "la", "he", "thong", "nguoi", "dung", "cho", "phep", "phai"}
        has_vi_common = any(w in vi_common_words for w in words)
        if has_vi_common and vi_char_count > 0:
            return "vi"

        return "en"

    @classmethod
    def clean_bullet_points(cls, text: str) -> str:
        """Loại bỏ ký hiệu đầu dòng, chuẩn hóa bảng Markdown (| ... |) và giữ nguyên câu hoàn chỉnh."""
        lines = text.splitlines()
        cleaned_lines = []
        table_header_markers = (
            "mã fr", "mô tả yêu cầu chi tiết", "độ ưu tiên",
            "vai trò (role)", "mô tả & phạm vi quyền hạn chính",
        )
        priority_suffixes = {
            "cao (high)", "cao(high)", "trung bình (medium)", "trung bình(medium)",
            "thấp (low)", "thấp(low)", "high", "medium", "low", "cao", "trung bình", "thấp",
        }

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            # Xử lý dòng bảng dạng pipe "| ô 1 | ô 2 | ô 3 |" khi người dùng dán từ Word/Markdown
            if trimmed.startswith("|") and trimmed.endswith("|"):
                cells = [
                    " ".join(c.replace("\\|", "|").split())
                    for c in trimmed.strip("|").split("|")
                    if c.strip() and not re.match(r"^[\-:]+$", c.strip())
                ]
                if not cells:
                    continue
                joined_low = " | ".join(cells).lower()
                if "tài liệu phân tích nghiệp vụ" in joined_low:
                    continue
                if sum(1 for m in table_header_markers if m in joined_low) >= 2:
                    continue
                if len(cells) >= 3 and cells[-1].lower() in priority_suffixes:
                    cells = cells[:-1]
                trimmed = " — ".join(cells).replace(". ", "; ")
            else:
                # Xóa các tiền tố đầu dòng: 1., 1.1., a), -, *, •, >
                trimmed = re.sub(r"^[\s•\-\*\>]+", "", trimmed)
                trimmed = re.sub(r"^\d+(?:\.\d+)*[\.\)]\s*", "", trimmed)
                trimmed = re.sub(r"^[a-zA-Z][\.\)]\s*", "", trimmed)

            # Nếu là dòng bảng FR-xx hoặc quy tắc BR-xx có nhiều câu bên trong, nối bằng '; ' để không bị cắt đôi
            if re.match(r"^(FR-\d+|BR-\d+)\b", trimmed, flags=re.IGNORECASE):
                trimmed = trimmed.replace(". ", "; ")

            if trimmed:
                cleaned_lines.append(trimmed)
        return "\n".join(cleaned_lines)

    @classmethod
    def _expand_compound_clauses(cls, sentence: str) -> List[str]:
        """Tách câu ghép liệt kê nhiều hành động của hệ thống thành các câu yêu cầu nguyên tử."""
        # Ví dụ: "The system splits the text into requirements, classifies them as..., flags..., and generates..."
        en_match = re.match(
            r"^(The\s+system|The\s+application|The\s+tool|Users?)\s+(.+)$",
            sentence.rstrip(".!?"),
            flags=re.IGNORECASE,
        )
        if en_match:
            subject = en_match.group(1)
            predicate = en_match.group(2)
            # Tách tại dấu phẩy theo sau bởi động từ ngôi thứ 3 số ít phổ biến trong đặc tả
            parts = re.split(
                r",\s*(?:and\s+)?(?=(?:splits|classifies|flags|detects|generates|exports|validates|"
                r"stores|sends|allows|supports|provides|analyzes|reads|creates|updates|deletes)\b)",
                predicate,
                flags=re.IGNORECASE,
            )
            if len(parts) > 1:
                expanded = []
                for idx, part in enumerate(parts):
                    clean_part = part.strip().rstrip(",.")
                    # Thay đại từ "them" bằng danh từ "requirements" để câu đơn độc lập rõ nghĩa
                    clean_part = re.sub(r"\bclassifies\s+them\b", "classifies requirements", clean_part, flags=re.IGNORECASE)
                    if idx == 0:
                        expanded.append(f"{subject} {clean_part}.")
                    else:
                        subj_norm = "The system" if subject.lower().startswith("the") else subject
                        expanded.append(f"{subj_norm} {clean_part}.")
                return expanded
        return [sentence]

    @classmethod
    def segment(cls, raw_text: str) -> Tuple[List[str], str]:
        """Tách chuỗi văn bản thành danh sách các câu yêu cầu nguyên tử.

        Returns:
            Tuple[List[str], str]: (danh sách các câu ứng viên >= 4 từ, mã ngôn ngữ)
        """
        if not raw_text or not raw_text.strip():
            return [], "vi"

        normalized = unicodedata.normalize("NFC", raw_text)
        lang = cls.detect_language(normalized)
        cleaned_text = cls.clean_bullet_points(normalized)

        # 1. Bảo vệ số thập phân: thay thế dấu chấm trong 99.9 hoặc 1.5 bằng token tạm thời
        protected_text = re.sub(r"(\d+)\.(\d+)", r"\1__DECIMAL_DOT__\2", cleaned_text)

        # 2. Bảo vệ các từ viết tắt phổ biến
        for abbrev in ABBREVIATIONS:
            def replace_abbrev(match):
                return match.group(0).replace(".", "__ABBREV_DOT__")
            protected_text = re.sub(abbrev, replace_abbrev, protected_text, flags=re.IGNORECASE)

        # 3. Tách theo dấu kết thúc câu (. ! ?) hoặc xuống dòng (\n+)
        # Lưu ý: giữ dấu chấm phẩy (;) để không cắt vụn 1 dòng bảng biểu thành nhiều mảnh rời rạc
        sentences = re.split(r"(?<=[.!?])\s+|\n+", protected_text)

        # Kiểm tra xem tài liệu có phải là BRD có bảng FR-01..FR-xx chi tiết hay không
        has_structured_fr = bool(re.search(r"\bFR-0?1\b", normalized, flags=re.IGNORECASE))

        non_req_heading_pattern = re.compile(
            r"^(Topic\s+\d+\s*[—\-:]|Related\s+topics\s*:|"
            r"TÀI\s+LIỆU\s+PHÂN\s+TÍCH\s+NGHIỆP\s+VỤ|HỆ\s+THỐNG\s+QUẢN\s+LÝ\s+|"
            r"TỔNG\s+QUAN\s+DỰ\s+ÁN|ĐỐI\s+TƯỢNG\s+SỬ\s+DỤNG\s*&\s*PHÂN\s+QUYỀN|"
            r"ĐẶC\s+TẢ\s+YÊU\s+CẦU\s+CHỨC\s+NĂNG|QUY\s+TẮC\s+NGHIỆP\s+VỤ\s+CỐT\s+LÕI|"
            r"YÊU\s+CẦU\s+PHI\s+CHỨC\s+NĂNG|Mục\s+tiêu\s+chính\s*\(|"
            r"Phạm\s+vi\s+hệ\s+thống\s*\(|Trong\s+phạm\s+vi\s*\(In-Scope\)|"
            r"Outside\s+Scope\s*\(Out-of-Scope\)|Ngoài\s+phạm\s+vi\s*\(Out-of-Scope\)|"
            r"Phiên\s+bản\s*:\s*\d|Mã\s+dự\s+án\s*:|Vai\s+trò\s*\(Role\)\s*[—\-]|Mã\s+FR\s*[—\-])",
            flags=re.IGNORECASE,
        )

        # Các câu mô tả mục tiêu tổng quan chương 1 trong BRD (đã được cụ thể hóa ở bảng FR-01..FR-06)
        brd_overview_intro_pattern = re.compile(
            r"^(Hệ\s+thống\s+.*\s+được\s+xây\s+dựng\s+nhằm\s+số\s+hóa|"
            r"Tập\s+trung\s+hóa\s+dữ\s+liệu\s*:|"
            r"Tự\s+động\s+hóa\s+vận\s+hành\s*:|"
            r"Minh\s+bạch\s*&\s*Tự\s+phục\s+vụ\s*\(ESS\)\s*:|"
            r"Hỗ\s+trợ\s+ra\s+quyết\s+định\s*:)",
            flags=re.IGNORECASE,
        )

        candidate_requirements = []
        for s in sentences:
            # Khôi phục lại các token đã bảo vệ
            restored = s.replace("__DECIMAL_DOT__", ".").replace("__ABBREV_DOT__", ".")
            restored = restored.strip(" \t\n\r.;")
            if not restored:
                continue

            # Bỏ qua dòng tiêu đề tài liệu, tiêu đề chương mục, metadata hoặc phạm vi
            if non_req_heading_pattern.match(restored):
                continue

            # Nếu tài liệu đã có bảng đặc tả FR-01..FR-xx, bỏ qua đoạn văn giới thiệu tổng quan ở Chương 1
            if has_structured_fr and brd_overview_intro_pattern.match(restored):
                continue

            # Bỏ qua dòng toàn chữ IN HOA ngắn (tiêu đề chương mục trong Word)
            if restored.isupper() and len(restored.split()) <= 12:
                continue

            # Cắt bỏ nhãn mở đầu đoạn như "Objective:", "Problem description:", "Mục tiêu:"
            restored = re.sub(
                r"^(Objective|Problem\s+description|Mục\s+tiêu|Mô\s+tả\s+bài\s+toán)\s*:\s*",
                "",
                restored,
                flags=re.IGNORECASE,
            ).strip()

            words = restored.split()
            # Yêu cầu REQ-1.4: Lọc bỏ các mảnh văn bản nhỏ hơn 4 từ
            if len(words) >= 4:
                # Viết hoa chữ cái đầu và thêm dấu chấm kết câu chuẩn
                formatted = restored[0].upper() + restored[1:]
                if not formatted.endswith((".", "!", "?")):
                    formatted += "."
                for atomic in cls._expand_compound_clauses(formatted):
                    if len(atomic.split()) >= 4:
                        candidate_requirements.append(atomic)

        return candidate_requirements, lang
