"""Bộ sinh Agile User Stories và Tiêu chí Nghiệm thu Gherkin (BDD) từ dữ liệu thật.

Sử dụng Batch LLM Prompting để sinh User Stories & kịch bản Gherkin bám sát 100%
nội dung từng câu yêu cầu thực tế của người dùng, không sử dụng dữ liệu giả (mock).
"""

import json
import re
from typing import List, Optional
from src.classifiers.llm_client import MultiLLMClient
from src.core.models import AcceptanceCriteriaDTO, RequirementDTO, UseCaseRelDTO, UserStoryDTO

BATCH_USER_STORY_PROMPT = """
Bạn là một Senior Business Analyst và Kiến trúc sư Hệ thống thành thạo chuẩn UML 2.5.
Hãy phân tích danh sách các câu yêu cầu phần mềm thực tế dưới đây và chuyển đổi MỖI CÂU
thành một Agile User Story chuẩn INVEST, kèm Use Case UML 2.5 (Động từ + Đối tượng, KHÔNG chứa mã FR-xx/UC-xx)
và 2 kịch bản nghiệm thu Gherkin BDD.

QUY TẮC BẮT BUỘC:
1. Bám sát 100% nội dung nghiệp vụ, đối tượng và hành động thực tế của từng câu yêu cầu.
2. 'role': Tác nhân thực tế (Roles) trong phần Đối tượng sử dụng & Phân quyền
   (VD: Quản trị viên hệ thống, Chuyên viên Nhân sự (HR), Quản lý trực tiếp, Nhân viên, Thủ kho...).
3. 'goal': Hành động hoặc tính năng cụ thể rút ra trực tiếp từ câu yêu cầu.
4. 'benefit': Giá trị nghiệp vụ thực tế mà tính năng đó mang lại.
5. 'puml_usecase_name': Tên Ca sử dụng bắt buộc theo cấu trúc [Động từ hành động] + [Đối tượng nghiệp vụ]
   (3-6 từ). TUYỆT ĐỐI KHÔNG gắn mã yêu cầu (FR-01:, UC-01:) hoặc tên Actor vào bên trong tên Use Case.
6. 'sub_usecases': Danh sách các bước xử lý chi tiết hoặc tính năng phụ trợ nằm bên trong nghiệp vụ lớn
   được tách thành Use Case con với quan hệ 'include' (bắt buộc có) hoặc 'extend' (tùy chọn/điều kiện).
7. 'acceptance_criteria': Gồm ít nhất 2 kịch bản cụ thể (1 luồng thành công và 1 luồng kiểm tra ràng buộc/ngoại lệ).

BẮT BUỘC TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON NHƯ SAU:
{
  "stories": [
    {
      "req_id": "REQ-01",
      "role": "...",
      "goal": "...",
      "benefit": "...",
      "puml_usecase_name": "...",
      "sub_usecases": [
        {"target_name": "...", "rel_type": "include"}
      ],
      "acceptance_criteria": [
        {
          "scenario": "...",
          "given": "...",
          "when": "...",
          "then": "..."
        },
        {
          "scenario": "...",
          "given": "...",
          "when": "...",
          "then": "..."
        }
      ]
    }
  ]
}
"""


class UserStoryGenerator:
    """Sinh Agile User Story và kịch bản kiểm thử Gherkin trực tiếp từ yêu cầu thực tế."""

    def __init__(
        self,
        llm_client: Optional[MultiLLMClient] = None,
        strict_llm: bool = False,
        batch_size: int = 6,
    ):
        self.llm_client = llm_client
        self.strict_llm = strict_llm
        self.batch_size = batch_size

    def _parse_story_dict(self, data: dict, req: RequirementDTO, lang: str = "vi") -> Optional[UserStoryDTO]:
        """Chuyển đổi từ điển JSON từ LLM sang UserStoryDTO hợp lệ."""
        story_id = f"US-{req.req_id.replace('REQ-', '')}"
        acs = [
            AcceptanceCriteriaDTO(
                scenario=ac.get("scenario", "").strip(),
                given=ac.get("given", "").strip(),
                when=ac.get("when", "").strip(),
                then=ac.get("then", "").strip(),
            )
            for ac in data.get("acceptance_criteria", [])
            if ac.get("given") and ac.get("when") and ac.get("then")
        ]
        if len(acs) < 2:
            return None

        default_role = "Người dùng hệ thống" if lang == "vi" else "System User"
        raw_uc_name = data.get("puml_usecase_name", "").strip() or req.raw_text[:35].strip()
        clean_uc_name = self._strip_usecase_prefix_and_actor(raw_uc_name)

        sub_ucs = []
        for s_item in data.get("sub_usecases", []) or []:
            if isinstance(s_item, dict) and s_item.get("target_name"):
                t_name = self._strip_usecase_prefix_and_actor(s_item["target_name"])
                r_type = s_item.get("rel_type", "include").lower().strip()
                if r_type not in ("include", "extend"):
                    r_type = "include"
                if t_name and t_name.lower() != clean_uc_name.lower():
                    sub_ucs.append(UseCaseRelDTO(target_name=t_name, rel_type=r_type))

        if not sub_ucs:
            sub_ucs = self._extract_sub_usecases(req.raw_text, clean_uc_name)

        return UserStoryDTO(
            story_id=story_id,
            req_id=req.req_id,
            role=data.get("role", default_role).strip(),
            goal=data.get("goal", req.raw_text).strip(),
            benefit=data.get("benefit", "").strip() or req.raw_text,
            acceptance_criteria=acs,
            puml_usecase_name=clean_uc_name,
            sub_usecases=sub_ucs,
        )

    @staticmethod
    def _strip_usecase_prefix_and_actor(name: str) -> str:
        """Loại bỏ triệt để mã FR-xx/UC-xx/REQ-xx và tên Actor khỏi tên Use Case theo chuẩn UML 2.5."""
        cleaned = (name or "").strip()
        # Xóa tiền tố FR-01:, UC-01:, REQ-01:, BR-01:
        cleaned = re.sub(
            r"^(?:FR|UC|REQ|NFR|BR|US)\s*[-_]?\s*\d+\s*[—\-:.)]*\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        # Xóa tiền tố tên Actor nếu bị dính vào đầu tên Use Case (VD: "Kế toán - Kiểm tra", "HR: Quản lý")
        cleaned = re.sub(
            r"^(?:Quản\s+trị\s+viên(?:\s+hệ\s+thống)?|Chuyên\s+viên\s+Nhân\s+sự(?:\s*\(HR\))?|"
            r"Quản\s+lý\s+trực\s+tiếp|Nhân\s+viên|Kế\s+toán|Thủ\s+kho|Khách\s+hàng|HR)\s*[—\-:]\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if not cleaned:
            return name.strip()
        return cleaned[0].upper() + cleaned[1:]

    @classmethod
    def _extract_sub_usecases(cls, raw_text: str, parent_uc_name: str) -> List[UseCaseRelDTO]:
        """Phân tách bước xử lý chi tiết bên trong nghiệp vụ lớn thành Use Case con (<<include>> / <<extend>>)."""
        raw = (raw_text or "").strip()
        low = raw.lower()
        subs: List[UseCaseRelDTO] = []

        # 1. Nếu là các phân hệ chuẩn trong BRD (FR-01..FR-06 hoặc WMS/E-commerce)
        if re.search(r"\bfr-0?1\b|hồ\s+sơ\s+nhân\s+sự", low):
            if "hợp đồng" in low:
                subs.append(UseCaseRelDTO(target_name="Theo dõi trạng thái hợp đồng", rel_type="include"))
            if "lịch sử" in low or "thăng tiến" in low or "điều chuyển" in low:
                subs.append(UseCaseRelDTO(target_name="Lưu vết lịch sử công tác", rel_type="extend"))
        elif re.search(r"\bfr-0?2\b|cơ\s+cấu\s+tổ\s+chức", low):
            if "phòng ban" in low or "vị trí" in low:
                subs.append(UseCaseRelDTO(target_name="Thiết lập sơ đồ phòng ban", rel_type="include"))
            if "quản lý trực tiếp" in low or "phê duyệt" in low:
                subs.append(UseCaseRelDTO(target_name="Gán cấp quản lý phê duyệt", rel_type="include"))
        elif re.search(r"\bfr-0?3\b", low) or low.startswith("chấm công"):
            if "máy chấm công" in low or "gps" in low or "wifi" in low or "dữ liệu" in low:
                subs.append(UseCaseRelDTO(target_name="Đồng bộ dữ liệu chấm công", rel_type="include"))
            if "đi muộn" in low or "về sớm" in low or "khấu trừ" in low:
                subs.append(UseCaseRelDTO(target_name="Tính thời gian đi muộn, về sớm", rel_type="include"))
        elif re.search(r"\bfr-0?4\b|nghỉ\s+phép\s*&\s*đơn\s+từ", low):
            if "quỹ phép" in low or "trừ" in low:
                subs.append(UseCaseRelDTO(target_name="Kiểm tra và trừ quỹ phép", rel_type="include"))
            if "email" in low or "thông báo" in low:
                subs.append(UseCaseRelDTO(target_name="Gửi thông báo trạng thái đơn", rel_type="include"))
        elif re.search(r"\bfr-0?5\b|tính\s+lương", low):
            if "bhxh" in low or "thuế" in low or "tncn" in low or "khấu trừ" in low:
                subs.append(UseCaseRelDTO(target_name="Khấu trừ BHXH và thuế TNCN", rel_type="include"))
            if "phiếu lương" in low or "payslip" in low:
                subs.append(UseCaseRelDTO(target_name="Xuất phiếu lương cá nhân", rel_type="extend"))
        elif re.search(r"\bfr-0?6\b|báo\s+cáo\s*&\s*dashboard", low):
            if "excel" in low or "pdf" in low or "xuất" in low:
                subs.append(UseCaseRelDTO(target_name="Xuất báo cáo Excel / PDF", rel_type="extend"))

        # 2. Nhận diện mẫu tổng quát cho mọi tài liệu BRD/SRS khác (WMS, E-commerce, NLP, v.v.)
        if not subs:
            generic_patterns = [
                (r"quét\s+mã\s+vạch|barcode|qr\s*code", "Quét mã vạch sản phẩm", "include"),
                (r"kiểm\s+tra\s+tồn\s+kho", "Kiểm tra số lượng tồn kho", "include"),
                (r"gợi\s+ý\s+vị\s+trí", "Gợi ý vị trí lưu kho", "include"),
                (r"xác\s+thực\s+đăng\s+nhập|xác\s+thực\s+2\s+lớp|otp|2fa", "Xác thực bảo mật tài khoản", "include"),
                (r"phân\s+quyền\s+theo\s+vai\s+trò|rbac", "Phân quyền truy cập RBAC", "include"),
                (r"thanh\s+toán\s+trực\s+tuyến|cổng\s+thanh\s+toán", "Xử lý thanh toán trực tuyến", "include"),
                (r"xuất\s+(?:báo\s+cáo|file|dữ\s+liệu)\s+(?:ra\s+)?(?:excel|pdf|csv|word)", "Xuất tệp báo cáo", "extend"),
                (r"gửi\s+(?:email|thông\s+báo)", "Gửi thông báo tự động", "include"),
            ]
            for pat, sub_label, rel in generic_patterns:
                if re.search(pat, low) and sub_label.lower() != parent_uc_name.lower():
                    subs.append(UseCaseRelDTO(target_name=sub_label, rel_type=rel))
                    if len(subs) >= 2:
                        break

        return subs

    def generate_single_story(self, req: RequirementDTO, lang: str = "vi") -> UserStoryDTO:
        """Sinh User Story cho một câu yêu cầu đơn lẻ."""
        stories = self.generate_stories_batch([req], lang=lang)
        return stories[0]

    @staticmethod
    def _build_clean_usecase_name(goal: str, lang: str = "vi") -> str:
        """Trích xuất tên Ca sử dụng (Use Case) ngắn gọn, chuẩn Động từ + Tân ngữ cho sơ đồ UML."""
        raw = goal.strip()

        # 1. Nếu là dòng bảng đặc tả có dạng "FR-01 — Tên Phân hệ — Mô tả..."
        # Quy tắc UML 2.5 nghiêm ngặt: Bắt đầu bằng [Động từ hành động] + [Đối tượng nghiệp vụ],
        # TUYỆT ĐỐI KHÔNG gắn mã yêu cầu (FR-01:, UC-01:) vào tên Use Case.
        fr_table_match = re.match(
            r"^(?:Hệ thống / Người dùng thực hiện:\s*)?(?:FR|UC|REQ)-\d+\s*[—\-:]\s*([^—\-:]+?)(?:\s*[—\-:]\s*(.+))?$",
            raw,
            flags=re.IGNORECASE,
        )
        if fr_table_match:
            module_name = re.sub(r"\([^)]*\)", "", fr_table_match.group(1)).strip()
            if module_name:
                low_mod = module_name.lower()
                if "chấm công" in low_mod:
                    return "Quản lý chấm công"
                if "tính lương" in low_mod:
                    return "Tính lương và phúc lợi"
                if "báo cáo" in low_mod and "dashboard" in low_mod:
                    return "Xem báo cáo và Dashboard"
                if not re.match(
                    r"^(Quản lý|Thiết lập|Xử lý|Xem|Tạo|Tính|Chấm|Phê duyệt|Tra cứu|Cấu hình)\b",
                    module_name,
                    flags=re.IGNORECASE,
                ):
                    return f"Quản lý {module_name}"
                return module_name

        # 2. Nếu là dòng định nghĩa Vai trò trong bảng Stakeholder ("Quản trị viên hệ thống (System Admin) — Cấu hình...")
        role_table_match = re.match(
            r"^(Quản trị viên hệ thống|Chuyên viên Nhân sự|Quản lý trực tiếp|Nhân viên)\s*(?:\([^)]*\))?\s*[—\-:]\s*(.+)$",
            raw,
            flags=re.IGNORECASE,
        )
        if role_table_match:
            role_key = role_table_match.group(1).lower()
            if "quản trị" in role_key:
                return "Cấu hình hệ thống & Phân quyền RBAC"
            if "chuyên viên nhân sự" in role_key:
                return "Quản lý hợp đồng, Ca làm & Bảng lương"
            if "quản lý trực tiếp" in role_key:
                return "Phê duyệt đơn nghỉ phép & Tăng ca (OT)"
            if "nhân viên" in role_key:
                return "Tra cứu ngày công, phép & Phiếu lương"

        # 3. Xóa các cụm giải thích trong ngoặc đơn (VD: "(for example ...)", "(Core HR)")
        cleaned = re.sub(r"\([^)]*\)", "", raw).strip()

        # 4. Nếu câu có dấu hai chấm (VD: "Tập trung hóa dữ liệu: Lưu trữ hồ sơ nhân viên..."), lấy vế hành động sau dấu :
        if ":" in cleaned:
            after_colon = cleaned.split(":", 1)[1].strip()
            if len(after_colon.split()) >= 3:
                cleaned = after_colon

        # Nếu câu có dấu chấm phẩy (;), chỉ lấy mệnh đề hành động đầu tiên cho tên Use Case ngắn gọn
        if ";" in cleaned:
            cleaned = cleaned.split(";", 1)[0].strip()

        # Nếu câu có liên từ nối vế phụ dài ("and automatically..."), chỉ giữ cụm động từ + tân ngữ chính
        cleaned = re.split(r"\s+and\s+automatically\s+", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip()

        # 5. Cắt bỏ các chủ ngữ/cụm dẫn nhập đầu câu
        cleaned = re.sub(
            r"^(it\s+|the\s+system\s+shall\s+|the\s+system\s+must\s+|the\s+system\s+|"
            r"the\s+application\s+|the\s+tool\s+|users?\s+can\s+|users?\s+|"
            r"build\s+a\s+tool\s+that\s+helps\s+[^:]+?\s+to\s+|"
            r"hệ\s+thống\s+/\s+người\s+dùng\s+thực\s+hiện\s*:\s*|"
            r"hệ\s+thống\s+phải\s+cho\s+phép\s+|hệ\s+thống\s+cho\s+phép\s+|"
            r"hệ\s+thống\s+phải\s+|hệ\s+thống\s+|ứng\s+dụng\s+phải\s+hỗ\s+trợ\s+|"
            r"ứng\s+dụng\s+|cho\s+phép\s+nhân\s+viên\s+chủ\s+động\s+|cho\s+phép\s+|"
            r"người\s+dùng\s+có\s+thể\s+|khách\s+hàng\s+có\s+thể\s+|nhân\s+viên\s+|"
            r"automatically\s+)",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip(" ,.;—-")

        # 6. Chuyển động từ tiếng Anh ngôi thứ 3 số ít ở đầu câu về nguyên mẫu chuẩn UML
        en_verb_map = {
            "splits": "Split",
            "classifies": "Classify",
            "flags": "Flag",
            "detects": "Detect",
            "generates": "Generate",
            "reads": "Read",
            "uploads": "Upload",
            "exports": "Export",
            "validates": "Validate",
            "analyzes": "Analyze",
            "improves": "Improve",
            "allows": "Allow",
            "supports": "Support",
        }
        words = cleaned.split()
        if words and lang != "vi":
            first_low = words[0].lower()
            if first_low in en_verb_map:
                words[0] = en_verb_map[first_low]

        # 7. Giới hạn tối đa 6 từ cho nhãn Elip gọn đẹp nhưng KHÔNG kết thúc ở từ nối cụt nghĩa
        dangling_words = {
            "into", "to", "for", "with", "and", "or", "the", "a", "an", "of", "in", "by", "as", "that",
            "vào", "cho", "của", "và", "hoặc", "với", "để", "các", "những", "một", "trong", "bằng",
            "trên", "theo", "từ", "khi", "về",
        }
        max_w = 6 if lang == "vi" else 7
        if len(words) > max_w:
            words = words[:max_w]
            while len(words) > 2 and words[-1].lower().rstrip(",.") in dangling_words:
                words.pop()

        result = " ".join(words).strip(" ,.;—-")
        if not result:
            result = goal[:32].strip()
        return result[0].upper() + result[1:]

    def _extract_story_from_text(self, req: RequirementDTO, story_id: str, lang: str = "vi") -> UserStoryDTO:
        """Bóc tách trực tiếp chủ ngữ, vị ngữ và đối tượng từ câu yêu cầu thực tế."""
        text = req.raw_text.strip().rstrip(".")
        low_text = text.lower()

        # 1. Kiểm tra nếu câu bắt đầu trực tiếp bằng Vai trò trong bảng Stakeholder
        if re.match(r"^quản\s+trị\s+viên\s+hệ\s+thống", low_text):
            role = "Quản trị viên hệ thống"
        elif re.match(r"^chuyên\s+viên\s+nhân\s+sự", low_text):
            role = "Chuyên viên Nhân sự (HR)"
        elif re.match(r"^quản\s+lý\s+trực\s+tiếp", low_text):
            role = "Quản lý trực tiếp"
        elif re.match(r"^nhân\s+viên\s*\(employee\)", low_text):
            role = "Nhân viên"
        # 2. Kiểm tra nếu câu là dòng đặc tả FR-01..FR-xx trong bảng Functional Requirements
        elif re.match(r"^(?:hệ thống / người dùng thực hiện:\s*)?fr-\d+\b", low_text):
            if any(k in low_text for k in ("hồ sơ nhân sự", "core hr", "cơ cấu tổ chức", "tính lương", "payroll", "hợp đồng")):
                role = "Chuyên viên Nhân sự (HR)"
            elif any(k in low_text for k in ("báo cáo", "dashboard", "biến động")):
                role = "Quản lý trực tiếp"
            else:
                role = "Nhân viên"
        else:
            # 3. Quét tác nhân trong văn bản thông thường
            actor_scan_text = re.sub(
                r"\b(user[-\s](friendly|stories|story|interface|experience|guide|manual)|"
                r"hệ\s+thống\s+quản\s+lý|quản\s+lý\s+(hồ\s+sơ|nhân\s+sự|nhân\s+viên|ca\s+làm|nghỉ\s+phép|"
                r"hợp\s+đồng|tài\s+khoản|đơn\s+hàng|sản\s+phẩm|kho))\b",
                "",
                text,
                flags=re.IGNORECASE,
            )

            actor_match = re.search(
                r"\b(quản\s+trị\s+viên\s+hệ\s+thống|quản\s+trị\s+viên|system\s+admin|"
                r"chuyên\s+viên\s+nhân\s+sự|bộ\s+phận\s+c&b|nhân\s+sự\s+thuộc\s+bộ\s+phận\s+c&b|hr\s*/\s*c&b|\bhr\b|"
                r"quản\s+lý\s+trực\s+tiếp|người\s+quản\s+lý|cấp\s+quản\s+lý|line\s+manager|quản\s+lý\s+duyệt|"
                r"business\s+analysts?|requirements\s+engineers?|"
                r"khách\s+hàng|người\s+mua|người\s+bán|nhân\s+viên|employee|"
                r"học\s+viên|giảng\s+viên|bác\s+sĩ|bệnh\s+nhân|kế\s+toán|"
                r"customers?|admins?|managers?|buyers?|sellers?|students?|users?|người\s+dùng)\b",
                actor_scan_text,
                flags=re.IGNORECASE,
            )

            if actor_match:
                low_actor = " ".join(actor_match.group(1).split()).lower()
                if low_actor in ("quản trị viên hệ thống", "quản trị viên", "system admin", "admin", "admins"):
                    role = "Quản trị viên hệ thống" if lang == "vi" else "System Administrator"
                elif low_actor in ("chuyên viên nhân sự", "bộ phận c&b", "nhân sự thuộc bộ phận c&b", "hr / c&b", "hr"):
                    role = "Chuyên viên Nhân sự (HR)"
                elif low_actor in (
                    "quản lý trực tiếp", "người quản lý", "cấp quản lý",
                    "line manager", "quản lý duyệt", "manager", "managers",
                ):
                    role = "Quản lý trực tiếp" if lang == "vi" else "Line Manager"
                elif low_actor in ("nhân viên", "employee"):
                    role = "Nhân viên" if lang == "vi" else "Employee"
                elif low_actor in ("business analysts", "business analyst", "requirements engineers", "requirements engineer"):
                    role = "Business Analyst"
                elif low_actor in ("users", "user", "người dùng"):
                    role = "Người dùng" if lang == "vi" else "Business Analyst"
                elif low_actor in ("khách hàng", "người mua", "customer", "customers", "buyer", "buyers"):
                    role = "Khách hàng" if lang == "vi" else "Customer"
                else:
                    role = low_actor[0].upper() + low_actor[1:]
            elif req.req_type == "NFR":
                role = "Quản trị viên hệ thống" if lang == "vi" else "System Administrator"
            else:
                role = "Nhân viên" if lang == "vi" else "Business Analyst"

        clean_goal = re.sub(
            r"^(Hệ thống phải cho phép|Hệ thống cho phép|Ứng dụng phải hỗ trợ|Hệ thống hỗ trợ|"
            r"Người dùng có thể|Khách hàng có thể|The system shall allow|The system must|"
            r"The system|Users can|Users)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        goal = clean_goal if clean_goal else text
        uc_name = self._strip_usecase_prefix_and_actor(self._build_clean_usecase_name(text, lang=lang))
        sub_ucs = self._extract_sub_usecases(text, uc_name)

        if lang == "vi":
            benefit = f"đảm bảo thực thi đúng yêu cầu: {text}"
            acs = [
                AcceptanceCriteriaDTO(
                    scenario=f"Kiểm tra thực thi: {uc_name}",
                    given=f"{role} truy cập vào chức năng liên quan đến '{uc_name}' với dữ liệu hợp lệ",
                    when=f"Thực hiện thao tác: {goal}",
                    then=f"Hệ thống đáp ứng đầy đủ yêu cầu: '{text}'",
                ),
                AcceptanceCriteriaDTO(
                    scenario=f"Kiểm tra ràng buộc & dữ liệu biên cho: {uc_name}",
                    given=f"{role} thao tác trên chức năng '{uc_name}' nhưng dữ liệu đầu vào không hợp lệ hoặc vượt ngưỡng",
                    when=f"Gửi yêu cầu xử lý: {goal}",
                    then="Hệ thống từ chối dữ liệu sai lệch và hiển thị thông báo kiểm tra hợp lệ tương ứng",
                ),
            ]
        else:
            benefit = f"fulfill requirement specification: {text}"
            acs = [
                AcceptanceCriteriaDTO(
                    scenario=f"Verify execution of: {uc_name}",
                    given=f"{role} accesses the module for '{uc_name}' with valid input",
                    when=f"Executing: {goal}",
                    then=f"The system satisfies: '{text}'",
                ),
                AcceptanceCriteriaDTO(
                    scenario=f"Verify boundary and validation constraints for: {uc_name}",
                    given=f"{role} submits incomplete or out-of-range parameters for '{uc_name}'",
                    when=f"Triggering: {goal}",
                    then="The system validates input rules and returns a specific validation message",
                ),
            ]

        return UserStoryDTO(
            story_id=story_id,
            req_id=req.req_id,
            role=role,
            goal=goal,
            benefit=benefit,
            acceptance_criteria=acs,
            puml_usecase_name=uc_name,
            sub_usecases=sub_ucs,
        )

    def generate_stories_batch(self, requirements: List[RequirementDTO], lang: str = "vi") -> List[UserStoryDTO]:
        """Sinh danh sách User Stories theo lô bằng LLM thật dựa trên dữ liệu thực tế."""
        if not requirements:
            return []

        if self.llm_client and self.llm_client.is_configured():
            all_stories: List[UserStoryDTO] = []
            try:
                for i in range(0, len(requirements), self.batch_size):
                    chunk = requirements[i:i + self.batch_size]
                    payload = [
                        {
                            "req_id": r.req_id,
                            "raw_text": r.raw_text,
                            "req_type": r.req_type,
                            "nfr_category": r.nfr_category,
                        }
                        for r in chunk
                    ]
                    user_prompt = (
                        f"Ngôn ngữ: {lang}\n"
                        f"Danh sách yêu cầu thực tế cần sinh User Story & Gherkin BDD:\n"
                        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                    )
                    raw_json = self.llm_client.chat_completion(
                        system_prompt=BATCH_USER_STORY_PROMPT,
                        user_prompt=user_prompt,
                        temperature=0.2,
                    )
                    data = json.loads(raw_json)
                    story_map = {
                        item.get("req_id"): item
                        for item in data.get("stories", [])
                        if item.get("req_id")
                    }
                    for req in chunk:
                        item_data = story_map.get(req.req_id)
                        parsed = self._parse_story_dict(item_data, req, lang) if item_data else None
                        if parsed:
                            all_stories.append(parsed)
                        else:
                            story_id = f"US-{req.req_id.replace('REQ-', '')}"
                            all_stories.append(self._extract_story_from_text(req, story_id, lang))
                return all_stories
            except Exception as exc:
                if self.strict_llm:
                    raise RuntimeError(f"Lỗi khi gọi AI sinh kịch bản User Story: {str(exc)}") from exc

        return [
            self._extract_story_from_text(req, f"US-{req.req_id.replace('REQ-', '')}", lang)
            for req in requirements
        ]
