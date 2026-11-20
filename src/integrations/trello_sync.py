"""Mô-đun tích hợp đồng bộ User Stories sang Trello Kanban Board.

Hỗ trợ xuất tệp JSON cấu trúc Trello Board hoàn chỉnh (danh sách cột Backlog,
các thẻ Cards, nhãn và mô tả) và tạo thẻ trực tiếp qua Trello REST API.
"""

import json
from typing import Any, Dict, List
import requests
from src.core.models import UserStoryDTO


class TrelloSync:
    """Xử lý đồng bộ User Stories sang Trello."""

    @staticmethod
    def format_card_description(us: UserStoryDTO) -> str:
        """Định dạng mô tả thẻ Trello theo chuẩn Markdown."""
        lines = [
            f"**Mã yêu cầu:** {us.req_id} | **Ca sử dụng:** {us.puml_usecase_name or 'N/A'}",
            "",
            "**Agile User Story:**",
            f"- Là một: {us.role}",
            f"- Tôi muốn: {us.goal}",
            f"- Để: {us.benefit}",
            "",
            "**Tiêu chí Nghiệm thu (Acceptance Criteria):**"
        ]
        for ac in us.acceptance_criteria:
            lines.extend([
                f"- [ ] **{ac.scenario}**",
                f"  - GIVEN {ac.given}",
                f"  - WHEN {ac.when}",
                f"  - THEN {ac.then}"
            ])
        return "\n".join(lines)

    @classmethod
    def generate_board_json(cls, stories: List[UserStoryDTO], board_name: str = "BA-Gen Product Backlog") -> str:
        """Sinh tệp JSON Trello Board hoàn chỉnh có thể import thẳng vào Trello/Power-Ups."""
        board_data = {
            "name": board_name,
            "desc": "Bảng Product Backlog sinh tự động bởi hệ thống BA-Gen",
            "lists": [
                {"name": "📋 Product Backlog (To Do)", "id": "list_todo"},
                {"name": "⚡ In Progress", "id": "list_doing"},
                {"name": "✅ Done / Accepted", "id": "list_done"}
            ],
            "cards": [
                {
                    "name": f"[{us.story_id}] Là một {us.role}, tôi muốn {us.goal}",
                    "desc": cls.format_card_description(us),
                    "idList": "list_todo",
                    "due": None
                }
                for us in stories
            ]
        }
        return json.dumps(board_data, ensure_ascii=False, indent=2)

    @classmethod
    def sync_to_trello_api(
        cls,
        api_key: str,
        token: str,
        list_id: str,
        stories: List[UserStoryDTO],
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Tạo các Cards trên danh sách Trello thông qua Trello REST API."""
        url = "https://api.trello.com/1/cards"
        created_cards = []
        errors = []

        for us in stories:
            card_name = f"[{us.story_id}] Là một {us.role}, tôi muốn {us.goal}"
            card_desc = cls.format_card_description(us)

            params = {
                "key": api_key.strip(),
                "token": token.strip(),
                "idList": list_id.strip(),
                "name": card_name[:150],
                "desc": card_desc
            }

            try:
                resp = requests.post(url, params=params, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    created_cards.append({
                        "story_id": us.story_id,
                        "card_id": data.get("id"),
                        "short_url": data.get("shortUrl")
                    })
                else:
                    errors.append({"story_id": us.story_id, "status": resp.status_code, "error": resp.text})
            except Exception as e:
                errors.append({"story_id": us.story_id, "error": str(e)})

        return {
            "success_count": len(created_cards),
            "created_cards": created_cards,
            "errors": errors
        }
