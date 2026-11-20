"""Bộ kiểm thử tích hợp cho RequirementAnalysisFacade (Facade Pattern)."""

from src.core.database import DatabaseManager
from src.core.facade import RequirementAnalysisFacade


def test_facade_end_to_end_analysis():
    db = DatabaseManager(":memory:")
    facade = RequirementAnalysisFacade(db_manager=db)

    input_text = """
    1. Khách hàng có thể đăng ký tài khoản mới bằng số điện thoại.
    2. Thời gian phản hồi phải cực nhanh và thân thiện dưới 1.5 giây.
    """
    result = facade.analyze_document(
        source=input_text,
        filename="test_input.txt",
        project_name="Dự án Demo Facade"
    )

    assert result.project.project_name == "Dự án Demo Facade"
    assert len(result.requirements) >= 2
    assert len(result.user_stories) >= 2
    assert "total_execution_sec" in result.timings
    assert result.plantuml_code != ""

    docx_bytes = facade.export_srs_docx()
    assert len(docx_bytes) > 100

    md_text = facade.export_srs_markdown()
    assert "TÀI LIỆU ĐẶC TẢ" in md_text


def test_facade_human_in_the_loop():
    db = DatabaseManager(":memory:")
    facade = RequirementAnalysisFacade(db_manager=db)

    input_text = "Hệ thống phải chạy thật nhanh và mượt mà."
    result = facade.analyze_document(source=input_text, filename="vague.txt")

    req_id = result.requirements[0].req_id
    assert result.requirements[0].is_ambiguous is True

    # Thao tác áp dụng SMART
    facade.apply_smart_rewrite(req_id)
    assert facade.current_requirements[0].is_ambiguous is False

    # Thao tác đổi nhãn FR/NFR
    facade.update_requirement_type(req_id, new_type="FR")
    assert facade.current_requirements[0].req_type == "FR"
