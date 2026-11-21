"""Bộ xuất bản Tài liệu Đặc tả Yêu cầu Phần mềm (SRS) theo Builder Pattern.

Hỗ trợ xuất sang định dạng Word (.docx) và Markdown (.md) tuân thủ
chuẩn cấu trúc IEEE 830 / ISO/IEC/IEEE 29148:2018.
"""

import io
from typing import List, Optional
from src.core.models import ProjectDTO, RequirementDTO, UserStoryDTO


class SRSBuilder:
    """Xây dựng tài liệu SRS chuẩn mực theo từng phần (Chương mục)."""

    def __init__(self):
        self.project: Optional[ProjectDTO] = None
        self.requirements: List[RequirementDTO] = []
        self.user_stories: List[UserStoryDTO] = []

    def set_project(self, project: ProjectDTO) -> "SRSBuilder":
        self.project = project
        return self

    def set_requirements(self, reqs: List[RequirementDTO]) -> "SRSBuilder":
        self.requirements = reqs
        return self

    def set_user_stories(self, stories: List[UserStoryDTO]) -> "SRSBuilder":
        self.user_stories = stories
        return self

    def export_markdown(self) -> str:
        """Kết xuất toàn bộ tài liệu SRS sang định dạng Markdown chuẩn."""
        p_name = self.project.project_name if self.project else "Hệ thống Phần mềm"
        lang = self.project.language if self.project else "vi"

        lines = [
            "# TÀI LIỆU ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS)",
            f"**Dự án:** {p_name}  ",
            "**Tiêu chuẩn áp dụng:** IEEE 830-1998 / ISO/IEC/IEEE 29148:2018  ",
            f"**Ngôn ngữ tài liệu:** {'Tiếng Việt' if lang == 'vi' else 'English'}  ",
            "\n---\n",
            "## 1. Giới thiệu & Phạm vi Hệ thống",
            (
                f"Tài liệu này xác định các đặc tả yêu cầu cho dự án **{p_name}**. "
                "Mục đích nhằm làm rõ phạm vi chức năng, tiêu chuẩn chất lượng phi chức năng và tiêu chí nghiệm thu."
            ),
            "\n## 2. Các Tác nhân Hệ thống (System Actors)",
        ]

        roles = sorted(list({us.role for us in self.user_stories if us.role}))
        if not roles:
            roles = ["Khách hàng (Customer)", "Quản trị viên (Administrator)", "Hệ thống (System)"]
        for r in roles:
            lines.append(f"- **{r}**")

        fr_list = [r for r in self.requirements if r.req_type == "FR"]
        lines.extend([
            "\n## 3. Danh mục Yêu cầu Chức năng (Functional Requirements)",
            "| Mã YC | Nội dung Đặc tả Yêu cầu | Độ tin cậy |",
            "| :--- | :--- | :---: |"
        ])
        for fr in fr_list:
            text = fr.smart_rewrite if fr.is_ambiguous and fr.smart_rewrite else fr.raw_text
            lines.append(f"| `{fr.req_id}` | {text} | {int(fr.confidence * 100)}% |")

        nfr_list = [r for r in self.requirements if r.req_type == "NFR"]
        lines.extend([
            "\n## 4. Danh mục Yêu cầu Phi chức năng (Non-Functional Requirements - ISO 25010)",
            "| Mã YC | Nhóm Chất lượng | Nội dung Đặc tả (Đã chuẩn hóa SMART) | Chỉ số Định lượng |",
            "| :--- | :--- | :--- | :---: |"
        ])
        for nfr in nfr_list:
            text = nfr.smart_rewrite if nfr.smart_rewrite else nfr.raw_text
            metric_status = "Đạt" if not nfr.missing_metric else "Cần bổ sung"
            lines.append(f"| `{nfr.req_id}` | {nfr.nfr_category or 'Chung'} | {text} | {metric_status} |")

        lines.extend([
            "\n## 5. Agile User Stories & Tiêu chí Nghiệm thu (Gherkin BDD)"
        ])
        for us in self.user_stories:
            lines.append(f"\n### {us.story_id} (Liên kết: `{us.req_id}`)")
            lines.append(f"> **Là một:** {us.role}  \n> **Tôi muốn:** {us.goal}  \n> **Để:** {us.benefit}")
            lines.append("\n**Tiêu chí nghiệm thu (Acceptance Criteria):**")
            for ac in us.acceptance_criteria:
                lines.append(f"- **Kịch bản:** *{ac.scenario}*")
                lines.append(f"  - **GIVEN** {ac.given}")
                lines.append(f"  - **WHEN** {ac.when}")
                lines.append(f"  - **THEN** {ac.then}")

        lines.extend([
            "\n## 6. Bảng Ánh xạ Tác nhân – Ca sử dụng (Actor – Use Case Mapping - UML 2.5)",
            (
                "| Mã Yêu cầu (Requirement) | Tác nhân (Actor) "
                "| Ca sử dụng Chính (Use Case) | Ca sử dụng Con (<<include>> / <<extend>>) |"
            ),
            "| :--- | :--- | :--- | :--- |"
        ])
        for us in self.user_stories:
            subs_text = ", ".join(
                f"`<<{s.rel_type}>>` {s.target_name}"
                for s in getattr(us, "sub_usecases", []) or []
            ) or "—"
            lines.append(f"| `{us.req_id}` | **{us.role}** | {us.puml_usecase_name} | {subs_text} |")

        return "\n".join(lines)

    def export_docx(self) -> bytes:
        """Xuất tài liệu sang tệp Microsoft Word (.docx) chuẩn bảng biểu và phông tiếng Việt."""
        import docx
        from docx.shared import Pt, Inches

        doc = docx.Document()

        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        p_name = self.project.project_name if self.project else "Hệ thống Phần mềm"

        title = doc.add_heading("TÀI LIỆU ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS)", level=0)
        title.paragraph_format.space_after = Pt(12)

        meta_p = doc.add_paragraph()
        meta_p.add_run(f"Dự án: {p_name}\n").bold = True
        meta_p.add_run("Tiêu chuẩn áp dụng: IEEE 830-1998 / ISO/IEC/IEEE 29148:2018\n")
        meta_p.add_run(f"Nguồn tệp phân tích: {self.project.source_filename if self.project else 'Trực tiếp'}\n")

        doc.add_heading("1. Giới thiệu & Phạm vi Hệ thống", level=1)
        doc.add_paragraph(
            f"Tài liệu này xác định chi tiết các đặc tả yêu cầu cho hệ thống '{p_name}', "
            "bao gồm các yêu cầu chức năng, ràng buộc chất lượng phi chức năng và kịch bản nghiệm thu kiểm thử hành vi."
        )

        doc.add_heading("2. Yêu cầu Chức năng (Functional Requirements)", level=1)
        fr_list = [r for r in self.requirements if r.req_type == "FR"]
        table_fr = doc.add_table(rows=1, cols=3)
        table_fr.style = "Table Grid"
        hdr_cells = table_fr.rows[0].cells
        hdr_cells[0].text = "Mã YC"
        hdr_cells[1].text = "Nội dung Yêu cầu"
        hdr_cells[2].text = "Độ tin cậy"

        for fr in fr_list:
            row_cells = table_fr.add_row().cells
            row_cells[0].text = fr.req_id
            row_cells[1].text = fr.smart_rewrite if fr.is_ambiguous and fr.smart_rewrite else fr.raw_text
            row_cells[2].text = f"{int(fr.confidence * 100)}%"

        doc.add_heading("3. Yêu cầu Phi chức năng (Non-Functional Requirements)", level=1)
        nfr_list = [r for r in self.requirements if r.req_type == "NFR"]
        table_nfr = doc.add_table(rows=1, cols=3)
        table_nfr.style = "Table Grid"
        hdr_nfr = table_nfr.rows[0].cells
        hdr_nfr[0].text = "Mã YC"
        hdr_nfr[1].text = "Nhóm (ISO 25010)"
        hdr_nfr[2].text = "Nội dung Đặc tả (Chuẩn SMART)"

        for nfr in nfr_list:
            row_cells = table_nfr.add_row().cells
            row_cells[0].text = nfr.req_id
            row_cells[1].text = nfr.nfr_category or "Chung"
            row_cells[2].text = nfr.smart_rewrite if nfr.smart_rewrite else nfr.raw_text

        doc.add_heading("4. Agile User Stories & Tiêu chí Nghiệm thu (Gherkin)", level=1)
        for us in self.user_stories:
            doc.add_heading(f"{us.story_id} (Liên kết: {us.req_id})", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Là một: {us.role}\nTôi muốn: {us.goal}\nĐể: {us.benefit}\n").italic = True

            for ac in us.acceptance_criteria:
                p_ac = doc.add_paragraph()
                p_ac.add_run(f"• Kịch bản: {ac.scenario}\n").bold = True
                p_ac.add_run(f"   GIVEN {ac.given}\n   WHEN {ac.when}\n   THEN {ac.then}")

        doc.add_heading("5. Bảng Ánh xạ Actor – Use Case (Chuẩn UML 2.5)", level=1)
        t_mat = doc.add_table(rows=1, cols=4)
        t_mat.style = "Table Grid"
        h = t_mat.rows[0].cells
        h[0].text = "Mã Yêu cầu"
        h[1].text = "Tác nhân (Actor)"
        h[2].text = "Ca sử dụng Chính (Use Case)"
        h[3].text = "Ca sử dụng Con (<<include>> / <<extend>>)"

        for us in self.user_stories:
            r = t_mat.add_row().cells
            r[0].text = us.req_id
            r[1].text = us.role
            r[2].text = us.puml_usecase_name
            subs_str = ", ".join(
                f"<<{s.rel_type}>> {s.target_name}"
                for s in getattr(us, "sub_usecases", []) or []
            ) or "—"
            r[3].text = subs_str

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()
