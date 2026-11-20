"""Điểm khởi chạy ứng dụng chính Streamlit (app.py) — BA-Gen.

Hoạt động 100% trên dữ liệu thật của người dùng và kết nối AI thực tế
(Groq, Google Gemini, OpenRouter, Ollama) — đã loại bỏ hoàn toàn mock data.
"""

from dotenv import load_dotenv
import streamlit as st

# Tải biến môi trường từ .env
load_dotenv()

from src.classifiers.llm_client import MultiLLMClient  # noqa: E402
from src.core.facade import RequirementAnalysisFacade  # noqa: E402
from src.ui.design_system import (  # noqa: E402
    build_pipeline_console_html,
    inject_design_system_css,
    render_command_header,
    render_empty_state_blueprint,
    render_html,
)
from src.ui.sidebar import render_sidebar  # noqa: E402
from src.ui.workbench import render_workbench  # noqa: E402

st.set_page_config(
    page_title="BA-Gen — Trợ lý Phân tích Yêu cầu Phần mềm",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    inject_design_system_css()

    # 1. Render Sidebar điều khiển và lấy cấu hình AI thực tế
    config = render_sidebar()

    # 2. Quản lý trạng thái phiên làm việc (Session State) với strict_llm=True
    llm_client = MultiLLMClient(
        provider=config["provider"],
        api_key=config["api_key"],
        model_name=config["model_name"],
    )
    if "facade" not in st.session_state:
        st.session_state["facade"] = RequirementAnalysisFacade(
            llm_client=llm_client,
            confidence_threshold=config["confidence_threshold"],
            force_llm_mode=True,
            strict_llm=True,
        )
    else:
        st.session_state["facade"].llm_client = llm_client
        st.session_state["facade"].strict_llm = True
        st.session_state["facade"].classifier.llm_client = llm_client
        st.session_state["facade"].classifier.llm_classifier.client = llm_client
        st.session_state["facade"].classifier.llm_classifier.strict_llm = True
        st.session_state["facade"].classifier.confidence_threshold = config["confidence_threshold"]
        st.session_state["facade"].classifier.force_llm_mode = True
        st.session_state["facade"].classifier.strict_llm = True
        st.session_state["facade"].ambiguity_detector.llm_client = llm_client
        st.session_state["facade"].ambiguity_detector.strict_llm = True
        st.session_state["facade"].user_story_gen.llm_client = llm_client
        st.session_state["facade"].user_story_gen.strict_llm = True

    if "project_name_input" not in st.session_state:
        st.session_state["project_name_input"] = ""
    if "analysis_result" not in st.session_state:
        st.session_state["analysis_result"] = None

    current_res = st.session_state["analysis_result"]
    active_lang = current_res.project.language if current_res else "vi"

    # 3. Banner đầu trang
    render_command_header(config, project_lang=active_lang)

    # 4. Khu vực Nhập tài liệu thực tế của dự án
    has_result = current_res is not None
    expander_label = (
        "1. Tài liệu & Nội dung Yêu cầu Dự án (Bấm vào đây để tải tài liệu mới hoặc chỉnh sửa)"
        if has_result
        else "1. Tải lên Tài liệu Dự án (.docx, .txt) hoặc Dán Yêu cầu Thực tế"
    )

    with st.expander(expander_label, expanded=(not has_result)):
        in_left, in_right = st.columns([3.1, 1.9])

        with in_right:
            project_name_val = st.text_input(
                "Tên Dự án / Hệ thống:",
                value=st.session_state["project_name_input"],
                placeholder="Nhập tên dự án của bạn (hoặc lấy tự động theo tên file)...",
            )
            st.session_state["project_name_input"] = project_name_val

            uploaded_file = st.file_uploader(
                "Tải file tài liệu yêu cầu thực tế (.docx hoặc .txt):",
                type=["docx", "txt"],
                help="Hỗ trợ đọc toàn bộ nội dung đoạn văn và bảng biểu trong file Word (.docx) tối đa 25 MB.",
            )

        with in_left:
            text_input = st.text_area(
                "Hoặc dán trực tiếp nội dung mô tả yêu cầu phần mềm thực tế vào đây:",
                height=185,
                placeholder="Dán nội dung tài liệu nghiệp vụ, biên bản họp khách hàng hoặc danh sách yêu cầu vào đây...",
            )
            char_count = len(text_input.strip())
            line_count = len([ln for ln in text_input.splitlines() if ln.strip()])
            st.caption(f"Độ dài văn bản hiện tại: {char_count} ký tự · {line_count} dòng")

        btn_run = st.button(
            "Bắt đầu Phân tích Yêu cầu Thực tế với AI",
            type="primary",
            use_container_width=True,
        )

    # 5. Thực thi phân tích 6 bước bằng kết nối AI thực tế
    pipeline_slot = st.empty()

    if btn_run:
        if not config.get("has_valid_key"):
            st.error(
                "Chưa có API Key hợp lệ! Vui lòng nhập API Key thực tế (Groq / Google Gemini / OpenRouter) "
                "ở thanh cài đặt bên trái để hệ thống kết nối AI phân tích tài liệu của bạn."
            )
            return

        facade: RequirementAnalysisFacade = st.session_state["facade"]

        if uploaded_file is not None:
            source = uploaded_file.getvalue()
            filename = uploaded_file.name
            size_bytes = len(source)
        elif text_input.strip():
            source = text_input.strip()
            filename = "tai_lieu_yeu_cau.txt"
            size_bytes = len(source.encode("utf-8"))
        else:
            st.warning("Vui lòng tải lên file tài liệu (.docx / .txt) hoặc dán nội dung yêu cầu cần phân tích.")
            return

        def on_pipeline_step(step_idx: int, stage_title: str, stage_detail: str):
            is_running = step_idx < 6
            render_html(
                build_pipeline_console_html(
                    active_step=step_idx,
                    status_title=f"AI đang xử lý Bước {min(step_idx, 5)}/6",
                    status_detail=stage_detail,
                    timings=facade.timings,
                    is_running=is_running,
                ),
                slot=pipeline_slot,
            )

        try:
            result = facade.analyze_document(
                source=source,
                filename=filename,
                file_size_bytes=size_bytes,
                project_name=st.session_state["project_name_input"].strip() or None,
                progress_callback=on_pipeline_step,
            )
            pipeline_slot.empty()
            st.session_state["analysis_result"] = result
            st.rerun()
        except Exception as e:
            pipeline_slot.empty()
            st.error(f"Không thể hoàn tất phân tích qua AI API: {str(e)}")

    # 6. Hiển thị kết quả phân tích hoặc hướng dẫn 3 bước
    if st.session_state["analysis_result"] is not None:
        render_workbench(
            st.session_state["facade"],
            st.session_state["analysis_result"],
            config=config,
        )
    else:
        render_empty_state_blueprint()


if __name__ == "__main__":
    main()
