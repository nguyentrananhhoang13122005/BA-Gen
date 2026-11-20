"""Bộ sinh Agile User Stories và Tiêu chí Nghiệm thu Gherkin (BDD).

Chuyển đổi từng câu yêu cầu sang cấu trúc Role - Goal - Benefit kèm tối thiểu
2 kịch bản Gherkin GIVEN / WHEN / THEN (luồng hợp lệ và luồng ngoại lệ/biên).
"""

import json
import re
from typing import List, Optional
from src.classifiers.llm_client import MultiLLMClient
from src.core.models import AcceptanceCriteriaDTO, RequirementDTO, UserStoryDTO

USER_STORY_PROMPT = """
Bạn là một Agile Product Owner / Business Analyst xuất sắc.
Hãy chuyển đổi câu yêu cầu phần mềm sau thành một Agile User Story chuẩn INVEST kèm tiêu chí nghiệm thu Gherkin BDD.
Yêu cầu:
1. Role: 'Khách hàng', 'Người dùng', hoặc 'Quản trị viên Hệ thống' / 'Chuyên viên Bảo mật' cho câu NFR.
2. Goal: Hành động người dùng muốn thực hiện.
3. Benefit: Giá trị mang lại.
4. Acceptance Criteria: BẮT BUỘC có ít nhất 2 kịch bản Gherkin (1 Thành công, 1 Ngoại lệ/Lỗi).
5. puml_usecase_name: Tên ca sử dụng ngắn gọn (dưới 6 từ).

BẮT BUỘC TRẢ VỀ ĐÚNG ĐỊNH DẠNG JSON NHƯ SAU:
{
  "role": "Người dùng",
  "goal": "đăng nhập vào hệ thống bằng email và mật khẩu",
  "benefit": "truy cập vào tài khoản cá nhân và quản lý đơn hàng",
  "acceptance_criteria": [
    {
      "scenario": "Đăng nhập thành công với thông tin hợp lệ",
      "given": "Người dùng đang ở trang đăng nhập và đã nhập đúng email cùng mật khẩu",
      "when": "Người dùng nhấn nút 'Đăng nhập'",
      "then": "Hệ thống xác thực thành công và chuyển hướng đến trang tổng quan trong vòng 2 giây"
    },
    {
      "scenario": "Đăng nhập thất bại do sai mật khẩu",
      "given": "Người dùng nhập email đúng nhưng mật khẩu sai",
      "when": "Người dùng nhấn nút 'Đăng nhập'",
      "then": "Hệ thống hiển thị thông báo lỗi 'Thông tin tài khoản không chính xác' và không chuyển trang"
    }
  ],
  "puml_usecase_name": "Đăng nhập hệ thống"
}
"""


class UserStoryGenerator:
    """Sinh User Story và kịch bản kiểm thử hành vi."""

    def __init__(self, llm_client: Optional[MultiLLMClient] = None):
        self.llm_client = llm_client

    def generate_single_story(self, req: RequirementDTO, lang: str = "vi") -> UserStoryDTO:
        """Sinh một User Story kèm 2 Gherkin ACs cho câu yêu cầu cụ thể."""
        story_id = f"US-{req.req_id.replace('REQ-', '')}"

        if self.llm_client and self.llm_client.is_configured():
            try:
                user_prompt = (
                    f"Ngôn ngữ: {lang}\n"
                    f"Câu yêu cầu: {req.raw_text}\n"
                    f"Loại: {req.req_type} ({req.nfr_category or ''})"
                )
                raw_json = self.llm_client.chat_completion(
                    system_prompt=USER_STORY_PROMPT,
                    user_prompt=user_prompt,
                    temperature=0.2
                )
                data = json.loads(raw_json)

                acs = [
                    AcceptanceCriteriaDTO(
                        scenario=ac.get("scenario", "Kịch bản nghiệm thu"),
                        given=ac.get("given", ""),
                        when=ac.get("when", ""),
                        then=ac.get("then", "")
                    )
                    for ac in data.get("acceptance_criteria", [])
                ]

                if len(acs) >= 2:
                    default_role = "Người dùng" if lang == "vi" else "User"
                    default_benefit = "đảm bảo nghiệp vụ" if lang == "vi" else "ensure business efficiency"
                    return UserStoryDTO(
                        story_id=story_id,
                        req_id=req.req_id,
                        role=data.get("role", default_role),
                        goal=data.get("goal", req.raw_text),
                        benefit=data.get("benefit", default_benefit),
                        acceptance_criteria=acs,
                        puml_usecase_name=data.get("puml_usecase_name", f"Xử lý {req.req_id}")
                    )
            except Exception:
                pass

        return self._generate_offline_story(req, story_id, lang)

    def _generate_offline_story(self, req: RequirementDTO, story_id: str, lang: str = "vi") -> UserStoryDTO:
        """Sinh User Story mẫu ngoại tuyến đảm bảo đủ tiêu chuẩn."""
        text = req.raw_text.strip().rstrip(".")

        if req.req_type == "NFR":
            role = "Quản trị viên Hệ thống" if lang == "vi" else "System Administrator"
            goal = f"thiết lập và duy trì ràng buộc: {text}" if lang == "vi" else f"enforce constraint: {text}"
            benefit = "hệ thống vận hành an toàn" if lang == "vi" else "system remains reliable"
            cat_name = req.nfr_category or ("Chất lượng" if lang == "vi" else "Quality")
            uc_name = f"Giám sát {cat_name}" if lang == "vi" else f"Monitor {cat_name}"
        else:
            role = "Khách hàng" if lang == "vi" else "User"
            prefix_pattern = (
                r"^(Hệ thống cho phép|Người dùng có thể|Khách hàng có thể|"
                r"The system shall allow users to|Users can)\s*"
            )
            clean_goal = re.sub(prefix_pattern, "", text, flags=re.IGNORECASE)
            goal = clean_goal[0].lower() + clean_goal[1:] if clean_goal else text
            benefit = "hoàn thành công việc nhanh chóng" if lang == "vi" else "achieve daily business tasks smoothly"
            uc_name = goal[:30].strip()

        if lang == "vi":
            acs = [
                AcceptanceCriteriaDTO(
                    scenario="Thực hiện thành công theo luồng chuẩn",
                    given=f"Người dùng có vai trò là '{role}' và hệ thống ở trạng thái sẵn sàng",
                    when=f"Người dùng thực hiện yêu cầu '{goal}'",
                    then="Hệ thống xử lý thành công, trả về kết quả hợp lệ và cập nhật dữ liệu liên quan"
                ),
                AcceptanceCriteriaDTO(
                    scenario="Xử lý ngoại lệ hoặc điều kiện không hợp lệ",
                    given="Dữ liệu đầu vào bị thiếu hoặc hệ thống gặp sự cố kết nối tạm thời",
                    when=f"Người dùng gửi yêu cầu '{goal}'",
                    then="Hệ thống ghi nhận nhật ký lỗi, hiển thị thông báo hướng dẫn rõ ràng"
                )
            ]
        else:
            acs = [
                AcceptanceCriteriaDTO(
                    scenario="Successful standard execution",
                    given=f"The actor is logged in as '{role}' and system is operational",
                    when=f"The actor triggers '{goal}'",
                    then="The system processes the request successfully and updates state"
                ),
                AcceptanceCriteriaDTO(
                    scenario="Exception or invalid input handling",
                    given="Input parameters are invalid or external network is degraded",
                    when=f"The actor triggers '{goal}'",
                    then="The system catches the error, logs it, and displays an informative notification"
                )
            ]

        return UserStoryDTO(
            story_id=story_id,
            req_id=req.req_id,
            role=role,
            goal=goal,
            benefit=benefit,
            acceptance_criteria=acs,
            puml_usecase_name=uc_name
        )

    def generate_stories_batch(self, requirements: List[RequirementDTO], lang: str = "vi") -> List[UserStoryDTO]:
        return [self.generate_single_story(req, lang=lang) for req in requirements]
