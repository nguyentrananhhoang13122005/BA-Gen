"""Điểm khởi chạy ứng dụng chính Streamlit (app.py) — BA-Gen.

Giao diện trực quan, dễ hiểu cho mọi người dùng, tích hợp kiểm tra trạng thái
API Key minh bạch và hiệu ứng chuyển động theo 6 bước phân tích.
"""

import os
import time
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

    # 1. Render Sidebar điều khiển và lấy cấu hình
    config = render_sidebar()

    # 2. Quản lý trạng thái phiên làm việc (Session State)
    if "facade" not in st.session_state:
        llm_client = MultiLLMClient(
            provider=config["provider"],
            api_key=config["api_key"],
            model_name=config["model_name"],
        )
        st.session_state["facade"] = RequirementAnalysisFacade(
            llm_client=llm_client,
            confidence_threshold=config["confidence_threshold"],
            force_llm_mode=config["force_llm"],
        )
    else:
        st.session_state["facade"].llm_client = MultiLLMClient(
            provider=config["provider"],
            api_key=config["api_key"],
            model_name=config["model_name"],
        )
        st.session_state["facade"].classifier.confidence_threshold = config["confidence_threshold"]
        st.session_state["facade"].classifier.force_llm_mode = config["force_llm"]

    if "raw_input_text" not in st.session_state:
        st.session_state["raw_input_text"] = ""
    if "project_name_input" not in st.session_state:
        st.session_state["project_name_input"] = "He-Thong-Thuong-Mai-Dien-Tu"
    if "analysis_result" not in st.session_state:
        st.session_state["analysis_result"] = None

    current_res = st.session_state["analysis_result"]
    active_lang = current_res.project.language if current_res else "vi"

    # 3. Banner đầu trang
    render_command_header(config, project_lang=active_lang)

    # 4. Khu vực Nhập văn bản / Tải file
    has_result = current_res is not None
    expander_label = (
        "1. Nhập nội dung bài toán hoặc Tải file tài liệu lên (Bấm vào đây để sửa hoặc đổi đề bài khác)"
        if has_result
        else "1. Nhập nội dung bài toán hoặc Tải file tài liệu (.docx, .txt)"
    )

    with st.expander(expander_label, expanded=(not has_result)):
        in_left, in_right = st.columns([3.1, 1.9])

        with in_right:
            project_name_val = st.text_input(
                "Đặt tên cho Dự án / Phần mềm của bạn:",
                value=st.session_state["project_name_input"],
            )
            st.session_state["project_name_input"] = project_name_val

            uploaded_file = st.file_uploader(
                "Tải file tài liệu có sẵn (.docx hoặc .txt):",
                type=["docx", "txt"],
                help="Hỗ trợ đọc cả chữ và bảng biểu trong file Word (.docx).",
            )

            if st.button("Dùng thử Bài mẫu Thương mại điện tử (1-Click)", use_container_width=True):
                sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_ecommerce_vi.txt")
                if os.path.exists(sample_path):
                    with open(sample_path, "r", encoding="utf-8") as f:
                        st.session_state["raw_input_text"] = f.read()
                    st.rerun()

        with in_left:
            text_input = st.text_area(
                "Hoặc dán trực tiếp nội dung mô tả yêu cầu phần mềm vào ô dưới đây:",
                value=st.session_state["raw_input_text"],
                height=185,
                placeholder=(
                    "Ví dụ:\n"
                    "1. Hệ thống cho phép khách hàng đăng ký tài khoản bằng số điện thoại.\n"
                    "2. Thời gian phản hồi trang thanh toán phải thật nhanh và dễ sử dụng..."
                ),
            )
            char_count = len(text_input.strip())
            line_count = len([ln for ln in text_input.splitlines() if ln.strip()])
            st.caption(f"Đang có: {char_count} ký tự · {line_count} dòng văn bản")

        btn_run = st.button(
            "Bắt đầu Phân tích Yêu cầu & Tạo Tài liệu Đặc tả",
            type="primary",
            use_container_width=True,
        )

    # 5. Thực thi phân tích 6 bước
    pipeline_slot = st.empty()

    if btn_run:
        if config.get("require_key") and not config.get("has_valid_key"):
            st.error(
                "Bạn đã bật tùy chọn 'Bắt buộc phải nhập API Key'. "
                "Vui lòng dán API Key ở thanh bên trái hoặc chuyển sang 'Chế độ Có sẵn (Offline)'."
            )
            return

        facade: RequirementAnalysisFacade = st.session_state["facade"]

        if uploaded_file is not None:
            source = uploaded_file.getvalue()
            filename = uploaded_file.name
            size_bytes = len(source)
        elif text_input.strip():
            source = text_input.strip()
            filename = "van_ban_nhap_truc_tiep.txt"
            size_bytes = len(source.encode("utf-8"))
        else:
            st.warning("Bạn chưa nhập văn bản hoặc tải file lên. Hãy bấm nút 'Dùng thử Bài mẫu' hoặc dán nội dung vào ô trên.")
            return

        def on_pipeline_step(step_idx: int, stage_title: str, stage_detail: str):
            is_running = step_idx < 6
            render_html(
                build_pipeline_console_html(
                    active_step=step_idx,
                    status_title=f"Đang xử lý Bước {min(step_idx, 5)}/6",
                    status_detail=stage_detail,
                    timings=facade.timings,
                    is_running=is_running,
                ),
                slot=pipeline_slot,
            )
            if is_running:
                time.sleep(0.14)

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
            st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {str(e)}")

    # 6. Hiển thị kết quả hoặc hướng dẫn 3 bước
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
