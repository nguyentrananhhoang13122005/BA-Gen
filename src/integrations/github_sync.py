"""Mô-đun tích hợp đồng bộ User Stories sang GitHub Issues.

Tạo tự động các GitHub Issues gắn nhãn (labels) và định dạng Markdown
chuẩn hóa chứa kịch bản kiểm thử hành vi Gherkin.
"""

import json
from typing import Any, Dict, List
import requests
from src.core.models import UserStoryDTO


class GitHubIssueSync:
    """Xử lý đồng bộ User Stories sang GitHub Issues."""

    @staticmethod
    def format_issue_body(us: UserStoryDTO) -> str:
        """Định dạng nội dung User Story thành Markdown hoàn chỉnh cho GitHub Issue."""
        lines = [
            f"**Mã yêu cầu gốc:** `{us.req_id}` | **Ca sử dụng:** *{us.puml_usecase_name or 'N/A'}*",
            "",
            "### 🎯 Agile User Story",
            f"> **Là một:** {us.role}  ",
            f"> **Tôi muốn:** {us.goal}  ",
            f"> **Để:** {us.benefit}",
            "",
            "### 📋 Tiêu chí Nghiệm thu (Gherkin BDD)"
        ]
        for ac in us.acceptance_criteria:
            lines.extend([
                f"- **Kịch bản:** *{ac.scenario}*",
                "  ```gherkin",
                f"  GIVEN {ac.given}",
                f"  WHEN  {ac.when}",
                f"  THEN  {ac.then}",
                "  ```"
            ])

        lines.extend([
            "",
            "---",
            "*Sinh tự động bởi hệ thống [BA-Gen (ReqAssist-NLP)](https://github.com/nguyentrananhhoang13122005/BA-Gen)*"
        ])
        return "\n".join(lines)

    @classmethod
    def sync_to_github_api(
        cls,
        repo: str,
        token: str,
        stories: List[UserStoryDTO],
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Tạo các Issue trên GitHub repository thông qua GitHub REST API."""
        clean_repo = repo.strip().replace("https://github.com/", "").strip("/")
        url = f"https://api.github.com/repos/{clean_repo}/issues"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token.strip()}",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        created_issues = []
        errors = []

        for us in stories:
            title = f"[{us.story_id}] Là một {us.role}, tôi muốn {us.goal}"
            body = cls.format_issue_body(us)
            payload = {
                "title": title[:200],
                "body": body,
                "labels": ["user-story", "enhancement"]
            }

            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    created_issues.append({
                        "story_id": us.story_id,
                        "issue_number": data.get("number"),
                        "html_url": data.get("html_url")
                    })
                else:
                    errors.append({"story_id": us.story_id, "status": resp.status_code, "error": resp.text})
            except Exception as e:
                errors.append({"story_id": us.story_id, "error": str(e)})

        return {
            "success_count": len(created_issues),
            "created_issues": created_issues,
            "errors": errors
        }

    @classmethod
    def generate_export_json(cls, stories: List[UserStoryDTO]) -> str:
        """Xuất danh sách User Stories dạng JSON chuẩn hóa để import vào GitHub CLI hoặc script."""
        payload = [
            {
                "title": f"[{us.story_id}] Là một {us.role}, tôi muốn {us.goal}",
                "body": cls.format_issue_body(us),
                "labels": ["user-story", "enhancement"]
            }
            for us in stories
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)
