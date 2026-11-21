"""Bộ sinh mã PlantUML và kết xuất ảnh Sơ đồ Use Case qua Kroki API.

Chuyển đổi các User Stories thành sơ đồ Use Case UML 2.5 trực quan hóa
quan hệ giữa Tác nhân (Actor) và Ca sử dụng (Use Case) mà không cần cài đặt
Java hay Graphviz trên máy người dùng.
"""

from typing import List, Optional, Tuple
import requests
from src.core.models import UserStoryDTO


class PlantUMLExporter:
    """Sinh cú pháp PlantUML và kết xuất ảnh đồ họa thông qua Kroki API."""

    def __init__(self, kroki_endpoint: str = "https://kroki.io/plantuml/png"):
        self.kroki_endpoint = kroki_endpoint

    def generate_plantuml_code(
        self,
        user_stories: List[UserStoryDTO],
        system_title: str = "Phạm vi Hệ thống",
        requirements: Optional[list] = None,
    ) -> str:
        """Sinh chuỗi mã nguồn @startuml ... @enduml chuẩn UML 2.5 (có <<include>> / <<extend>>)."""
        req_type_map = {}
        if requirements:
            for r in requirements:
                req_type_map[r.req_id] = r.req_type

        # Chỉ giữ các User Story thuộc nhóm Yêu cầu Chức năng (FR) trên sơ đồ Use Case
        fr_stories = [
            us for us in user_stories
            if req_type_map.get(us.req_id, "FR") == "FR"
        ]
        if not fr_stories:
            fr_stories = user_stories

        lines = [
            "@startuml",
            "left to right direction",
            "skinparam packageStyle rectangle",
            "skinparam monochrome false",
            "skinparam shadowing false",
            "skinparam defaultFontName Arial",
        ]

        # 1. Trích xuất danh sách Actor và gán ID
        actors = {}
        for us in fr_stories:
            role = us.role.strip() if us.role else "Người dùng"
            if role not in actors:
                actors[role] = f"ACTOR_{len(actors) + 1}"

        for role_name, actor_id in actors.items():
            clean_role = role_name.replace('"', "'")
            lines.append(f"actor \"{clean_role}\" as {actor_id}")

        lines.append("")
        safe_title = (system_title or "Hệ thống Phần mềm").replace('"', "'")
        lines.append(f"rectangle \"{safe_title}\" {{")

        # 2. Khai báo các Use Cases chính và Use Cases con (<<include>> / <<extend>>)
        usecases = []
        sub_uc_map = {}
        sub_links = []
        seen_parent_names = set()

        for idx, us in enumerate(fr_stories, start=1):
            uc_name = us.puml_usecase_name.strip() if us.puml_usecase_name else f"Xử lý {us.req_id}"
            uc_name = uc_name.replace('"', "'")
            low_key = uc_name.lower()
            if low_key in seen_parent_names:
                continue
            seen_parent_names.add(low_key)

            uc_id = f"UC_{idx:02d}"
            lines.append(f"  usecase \"{uc_name}\" as {uc_id}")
            role_key = us.role.strip() if us.role else "Người dùng"
            usecases.append((uc_id, role_key))

            for sub in getattr(us, "sub_usecases", []) or []:
                sub_name = (sub.target_name or "").strip().replace('"', "'")
                if not sub_name or sub_name.lower() == low_key:
                    continue
                sub_key = sub_name.lower()
                if sub_key not in sub_uc_map:
                    sub_id = f"SUB_UC_{len(sub_uc_map) + 1:02d}"
                    sub_uc_map[sub_key] = sub_id
                    lines.append(f"  usecase \"{sub_name}\" as {sub_id}")
                else:
                    sub_id = sub_uc_map[sub_key]
                rel_type = sub.rel_type if sub.rel_type in ("include", "extend") else "include"
                sub_links.append((uc_id, sub_id, rel_type))

        lines.append("}")
        lines.append("")

        # 3. Tạo các đường nối liên kết giữa Actor và Use Case chính (KHÔNG nối trực tiếp Actor tới Use Case con)
        for uc_id, role in usecases:
            actor_id = actors.get(role, "ACTOR_1")
            lines.append(f"{actor_id} --> {uc_id}")

        # 4. Tạo các đường nối <<include>> và <<extend>> từ Use Case chính sang Use Case con
        for parent_id, child_id, rel_type in sub_links:
            lines.append(f"{parent_id} ..> {child_id} : <<{rel_type}>>")

        lines.append("@enduml")
        return "\n".join(lines)

    def render_png_via_kroki(self, plantuml_code: str, timeout: float = 6.0) -> Optional[bytes]:
        """Gửi mã PlantUML đến Kroki API để lấy ảnh PNG."""
        try:
            headers = {"Content-Type": "text/plain; charset=utf-8"}
            response = requests.post(
                self.kroki_endpoint,
                data=plantuml_code.encode("utf-8"),
                headers=headers,
                timeout=timeout
            )
            if response.status_code == 200:
                return response.content
            return None
        except Exception:
            return None

    def export(
        self,
        user_stories: List[UserStoryDTO],
        system_title: str = "Hệ thống Phần mềm",
        requirements: Optional[list] = None,
    ) -> Tuple[str, Optional[bytes]]:
        """Sinh mã PlantUML và kết xuất ảnh cùng lúc."""
        puml_code = self.generate_plantuml_code(
            user_stories,
            system_title=system_title,
            requirements=requirements,
        )
        image_bytes = self.render_png_via_kroki(puml_code)
        return puml_code, image_bytes
