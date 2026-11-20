"""Bộ kiểm thử cho User Story Generator, SRS Builder và PlantUML Exporter."""

from src.core.models import ProjectDTO, RequirementDTO
from src.exporters.plantuml_exporter import PlantUMLExporter
from src.exporters.srs_builder import SRSBuilder
from src.generators.user_story_gen import UserStoryGenerator


def test_user_story_generator_offline():
    gen = UserStoryGenerator()
    req = RequirementDTO(
        req_id="REQ-01",
        raw_text="Khách hàng có thể thanh toán trực tuyến qua ví điện tử.",
        req_type="FR"
    )
    story = gen.generate_single_story(req, lang="vi")
    assert story.req_id == "REQ-01"
    assert story.role != ""
    assert story.goal != ""
    assert story.benefit != ""
    assert len(story.acceptance_criteria) >= 2


def test_plantuml_exporter():
    exporter = PlantUMLExporter()
    gen = UserStoryGenerator()
    req = RequirementDTO(req_id="REQ-01", raw_text="Người dùng đăng nhập.", req_type="FR")
    story = gen.generate_single_story(req, lang="vi")

    puml_code = exporter.generate_plantuml_code([story], system_title="Hệ thống Test")
    assert puml_code.startswith("@startuml")
    assert puml_code.endswith("@enduml")
    assert "usecase" in puml_code


def test_srs_builder():
    builder = SRSBuilder()
    proj = ProjectDTO(project_id="P1", project_name="E-Shop Test", source_filename="test.txt")
    req = RequirementDTO(req_id="REQ-01", raw_text="Người dùng đăng nhập.", req_type="FR")
    story = UserStoryGenerator().generate_single_story(req, lang="vi")

    builder.set_project(proj).set_requirements([req]).set_user_stories([story])

    md = builder.export_markdown()
    assert "TÀI LIỆU ĐẶC TẢ YÊU CẦU PHẦN MỀM" in md
    assert "E-Shop Test" in md
    assert "REQ-01" in md

    docx_bytes = builder.export_docx()
    assert len(docx_bytes) > 100
