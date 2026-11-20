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

    def generate_plantuml_code(self, user_stories: List[UserStoryDTO], system_title: str = "Phạm vi Hệ thống") -> str:
        """Sinh chuỗi mã nguồn @startuml ... @enduml hợp lệ."""
        lines = [
            "@startuml",
            "skinparam monochrome false",
            "skinparam shadowing true",
            "skinparam defaultFontName Arial",
            "left to right direction",
            f"rectangle \"{system_title}\" {{"
        ]

        # 1. Trích xuất danh sách Actor và gán ID
        actors = {}
        for us in user_stories:
            role = us.role.strip() if us.role else "Người dùng"
            if role not in actors:
                actors[role] = f"ACTOR_{len(actors) + 1}"

        # 2. Khai báo các Use Cases bên trong hình chữ nhật hệ thống
        usecases = {}
        for idx, us in enumerate(user_stories, start=1):
            uc_id = f"UC_{idx:02d}"
            uc_name = us.puml_usecase_name.strip() if us.puml_usecase_name else f"Xử lý {us.req_id}"
            uc_name = uc_name.replace('"', "'")
            lines.append(f"  usecase \"{uc_name}\" as {uc_id}")
            usecases[us.story_id] = (uc_id, us.role.strip())

        lines.append("}")

        # 3. Khai báo các Actor bên ngoài
        for role_name, actor_id in actors.items():
            clean_role = role_name.replace('"', "'")
            lines.append(f":{clean_role}: as {actor_id}")

        # 4. Tạo các đường nối liên kết giữa Actor và Use Case
        for story_id, (uc_id, role) in usecases.items():
            actor_id = actors.get(role, "ACTOR_1")
            lines.append(f"{actor_id} --> {uc_id}")

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

    def export(self, user_stories: List[UserStoryDTO], system_title: str = "Hệ thống Phần mềm") -> Tuple[str, Optional[bytes]]:
        """Sinh mã PlantUML và kết xuất ảnh cùng lúc."""
        puml_code = self.generate_plantuml_code(user_stories, system_title=system_title)
        image_bytes = self.render_png_via_kroki(puml_code)
        return puml_code, image_bytes
