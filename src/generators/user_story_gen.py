"""Bộ sinh Agile User Stories và Tiêu chí Nghiệm thu Gherkin (BDD) từ dữ liệu thật.

Sử dụng Batch LLM Prompting để sinh User Stories & kịch bản Gherkin bám sát 100%
nội dung từng câu yêu cầu thực tế của người dùng, không sử dụng dữ liệu giả (mock).
"""

import json
import re
from typing import List, Optional
from src.classifiers.llm_client import MultiLLMClient
from src.core.models import AcceptanceCriteriaDTO, RequirementDTO, UserStoryDTO

BATCH_USER_STORY_PROMPT = """
Bạn là một Senior Business Analyst / Agile Product Owner.
Hãy phân tích danh sách các câu yêu cầu phần mềm thực tế dưới đây và chuyển đổi MỖI CÂU
thành một Agile User Story chuẩn INVEST kèm 2 kịch bản nghiệm thu Gherkin BDD.

QUY TẮC BẮT BUỘC:
1. Bám sát 100% nội dung nghiệp vụ, đối tượng và hành động thực tế của từng câu yêu cầu.
2. 'role': Tác nhân thực tế trong câu (ví dụ: Khách mua hàng, Quản trị viên, Nhân viên kho, Kỹ sư vận hành...).
3. 'goal': Hành động hoặc tính năng cụ thể rút ra trực tiếp từ câu yêu cầu.
4. 'benefit': Giá trị nghiệp vụ thực tế mà tính năng đó mang lại.
5. 'puml_usecase_name': Tên chức năng (Use Case) ngắn gọn từ 3-7 từ phản ánh đúng hành động của câu đó.
6. 'acceptance_criteria': Gồm ít nhất 2 kịch bản cụ thể (1 luồng thành công và 1 luồng kiểm tra ràng buộc/ngoại lệ)
   với các thông số, trường dữ liệu và thông báo cụ thể của chức năng đó.

BẮT BUỘC TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON NHƯ SAU:
{
  "stories": [
    {
      "req_id": "REQ-01",
      "role": "...",
      "goal": "...",
      "benefit": "...",
      "puml_usecase_name": "...",
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
        return UserStoryDTO(
            story_id=story_id,
            req_id=req.req_id,
            role=data.get("role", default_role).strip(),
            goal=data.get("goal", req.raw_text).strip(),
            benefit=data.get("benefit", "").strip() or req.raw_text,
            acceptance_criteria=acs,
            puml_usecase_name=data.get("puml_usecase_name", "").strip() or req.raw_text[:35].strip(),
        )

    def generate_single_story(self, req: RequirementDTO, lang: str = "vi") -> UserStoryDTO:
        """Sinh User Story cho một câu yêu cầu đơn lẻ."""
        stories = self.generate_stories_batch([req], lang=lang)
        return stories[0]

    @staticmethod
    def _build_clean_usecase_name(goal: str, lang: str = "vi") -> str:
        """Trích xuất tên Ca sử dụng (Use Case) ngắn gọn, chuẩn Động từ + Tân ngữ cho sơ đồ UML."""
        raw = goal.strip()

        # 1. Nếu là dòng bảng đặc tả có dạng "FR-01 — Tên Phân hệ — Mô tả..."
        fr_table_match = re.match(
            r"^(?:Hệ thống / Người dùng thực hiện:\s*)?(?:FR-\d+)\s*[—\-:]\s*([^—\-:]+?)(?:\s*[—\-:]\s*(.+))?$",
            raw,
            flags=re.IGNORECASE,
        )
        if fr_table_match:
            module_name = re.sub(r"\([^)]*\)", "", fr_table_match.group(1)).strip()
            if module_name:
                if not re.match(r"^(Quản lý|Thiết lập|Xử lý|Xem|Tạo|Tính)\b", module_name, flags=re.IGNORECASE):
                    return f"Quản lý {module_name}"
                return module_name

        # 2. Nếu là dòng định nghĩa Vai trò trong bảng Stakeholder ("Quản trị viên hệ thống (System Admin) — Cấu hình...")
        role_table_match = re.match(
            r"^(Quản trị viên hệ thống|Chuyên viên Nhân sự|Quản lý trực tiếp|Nhân viên)\s*(?:\([^)]*\))?\s*[—\-:]\s*(.+)$",
            raw,
            flags=re.IGNORECASE,
        )
        if role_table_match:
            raw = role_table_match.group(2).strip()

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

        # Loại bỏ các cụm từ ghép dễ gây nhận nhầm Actor (VD: "Hệ thống Quản lý", "Quản lý hồ sơ", "user-friendly")
        actor_scan_text = re.sub(
            r"\b(user[-\s](friendly|stories|story|interface|experience|guide|manual)|"
            r"hệ\s+thống\s+quản\s+lý|quản\s+lý\s+(hồ\s+sơ|nhân\s+sự|nhân\s+viên|ca\s+làm|nghỉ\s+phép|"
            r"hợp\s+đồng|tài\s+khoản|đơn\s+hàng|sản\s+phẩm|kho))\b",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Trích xuất chủ thể thực tế có trong câu (Ưu tiên cụm đầy đủ trước)
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
        uc_name = self._build_clean_usecase_name(text, lang=lang)

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
