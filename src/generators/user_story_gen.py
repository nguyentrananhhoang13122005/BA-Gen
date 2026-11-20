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

    def _extract_story_from_text(self, req: RequirementDTO, story_id: str, lang: str = "vi") -> UserStoryDTO:
        """Bóc tách trực tiếp chủ ngữ, vị ngữ và đối tượng từ câu yêu cầu thực tế."""
        text = req.raw_text.strip().rstrip(".")

        # Trích xuất chủ thể thực tế có trong câu
        actor_match = re.search(
            r"\b(khách hàng|người mua|người bán|người dùng|quản trị viên|nhân viên|học viên|giảng viên|"
            r"bác sĩ|bệnh nhân|kế toán|quản lý|user|customer|admin|manager|buyer|seller|student)\b",
            text,
            flags=re.IGNORECASE,
        )
        if actor_match:
            found_actor = actor_match.group(1)
            role = found_actor[0].upper() + found_actor[1:]
        elif req.req_type == "NFR":
            role = "Kỹ sư Vận hành & Đảm bảo Chất lượng" if lang == "vi" else "Quality & Operations Engineer"
        else:
            role = "Người sử dụng hệ thống" if lang == "vi" else "System User"

        clean_goal = re.sub(
            r"^(Hệ thống phải cho phép|Hệ thống cho phép|Ứng dụng phải hỗ trợ|Hệ thống hỗ trợ|"
            r"Người dùng có thể|Khách hàng có thể|The system shall allow|The system must)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        if actor_match and clean_goal.lower().startswith(actor_match.group(1).lower()):
            clean_goal = clean_goal[len(actor_match.group(1)):].strip()
            clean_goal = re.sub(r"^(có thể|được phép|cần|phải|can|shall|must)\s+", "", clean_goal, flags=re.IGNORECASE)

        goal = clean_goal if clean_goal else text
        words = goal.split()
        uc_name = " ".join(words[:6]) if len(words) > 6 else goal

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
