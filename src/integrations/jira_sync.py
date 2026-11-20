"""Mô-đun tích hợp đồng bộ và xuất bản User Stories sang Atlassian Jira.

Hỗ trợ 2 phương thức:
1. Kết xuất tệp CSV chuẩn hóa Jira Cloud Issue Import (sử dụng được ngay mà không cần cấp quyền mạng).
2. Tạo Issue tự động qua Jira Cloud REST API v3.
"""

import csv
import io
from typing import Any, Dict, List
import requests
from requests.auth import HTTPBasicAuth
from src.core.models import UserStoryDTO


class JiraSync:
    """Xử lý đồng bộ và kết xuất User Stories sang Jira."""

    @staticmethod
    def generate_import_csv(stories: List[UserStoryDTO], project_key: str = "PROJ") -> str:
        """Sinh chuỗi CSV chuẩn hóa theo định dạng Jira Issue Import."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        # Tiêu đề cột chuẩn Jira
        writer.writerow(["Issue Type", "Summary", "Description", "Priority", "Labels", "Issue Id"])

        for us in stories:
            summary = f"[{us.story_id}] Là một {us.role}, tôi muốn {us.goal}"

            # Soạn thảo nội dung mô tả kèm Gherkin
            desc_lines = [
                f"*Mã yêu cầu gốc:* {us.req_id}",
                f"*Ca sử dụng:* {us.puml_usecase_name or 'N/A'}",
                "",
                "h3. Agile User Story",
                f"* *Là một:* {us.role}",
                f"* *Tôi muốn:* {us.goal}",
                f"* *Để:* {us.benefit}",
                "",
                "h3. Tiêu chí Nghiệm thu (Gherkin BDD)"
            ]
            for ac in us.acceptance_criteria:
                desc_lines.extend([
                    f"# *Kịch bản:* {ac.scenario}",
                    f"  * *GIVEN* {ac.given}",
                    f"  * *WHEN* {ac.when}",
                    f"  * *THEN* {ac.then}"
                ])

            description = "\n".join(desc_lines)
            writer.writerow([
                "Story",
                summary,
                description,
                "Medium",
                f"BA-Gen,{us.req_id}",
                us.story_id
            ])

        return output.getvalue()

    @staticmethod
    def sync_to_jira_api(
        domain: str,
        email: str,
        api_token: str,
        project_key: str,
        stories: List[UserStoryDTO],
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Tạo các Issue kiểu 'Story' trên Jira Cloud thông qua REST API v3."""
        clean_domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
        if not clean_domain.endswith(".atlassian.net"):
            clean_domain = f"{clean_domain}.atlassian.net"

        url = f"https://{clean_domain}/rest/api/3/issue"
        auth = HTTPBasicAuth(email, api_token)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        created_issues = []
        errors = []

        for us in stories:
            summary = f"[{us.story_id}] Là một {us.role}, tôi muốn {us.goal}"
            payload = {
                "fields": {
                    "project": {"key": project_key.upper()},
                    "summary": summary[:250],
                    "issuetype": {"name": "Story"},
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {"type": "text", "text": f"Là một: {us.role}\nTôi muốn: {us.goal}\nĐể: {us.benefit}"}
                                ]
                            }
                        ]
                    },
                    "labels": ["BA-Gen", us.req_id]
                }
            }

            try:
                resp = requests.post(url, json=payload, headers=headers, auth=auth, timeout=timeout)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    created_issues.append({"story_id": us.story_id, "jira_key": data.get("key"), "url": data.get("self")})
                else:
                    errors.append({"story_id": us.story_id, "status": resp.status_code, "error": resp.text})
            except Exception as e:
                errors.append({"story_id": us.story_id, "error": str(e)})

        return {
            "success_count": len(created_issues),
            "created_issues": created_issues,
            "errors": errors
        }
