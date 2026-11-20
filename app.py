"""Điểm khởi chạy ứng dụng chính Streamlit (app.py) — BA-Gen (ReqAssist-NLP).

Tự động hóa luồng từ tài liệu bài toán thô (.docx/.txt/paste) sang bộ đặc tả
phần mềm chuẩn hóa (SRS, User Story, Use Case Diagram) chỉ với 3 cú nhấp chuột.
"""

import os
from dotenv import load_dotenv
import streamlit as st

# Tải biến môi trường từ .env
load_dotenv()

from src.classifiers.llm_client import MultiLLMClient
from src.core.facade import RequirementAnalysisFacade
from src.ui.sidebar import render_sidebar
from src.ui.workbench import render_workbench

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="BA-Gen — Requirements Analysis Assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện hiện đại, chuyên nghiệp
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a237e;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #546e7a;
        margin-bottom: 20px;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown('<p class="main-header">📋 BA-Gen (ReqAssist-NLP)</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Trợ lý Phân tích Yêu cầu Phần mềm thông minh — Đọc tài liệu, Phân loại FR/NFR, '
        'Bắt lỗi Mơ hồ chuẩn SMART, Sinh Agile User Stories và Sơ đồ Use Case.</p>',
        unsafe_allow_html=True
    )

    # 1. Render Sidebar và lấy cấu hình
    config = render_sidebar()

    # 2. Quản lý trạng thái phiên làm việc (Session State)
    if "facade" not in st.session_state:
        llm_client = MultiLLMClient(
            provider=config["provider"],
            api_key=config["api_key"],
            model_name=config["model_name"]
        )
        st.session_state["facade"] = RequirementAnalysisFacade(
            llm_client=llm_client,
            confidence_threshold=config["confidence_threshold"],
            force_llm_mode=config["force_llm"]
        )
    else:
        # Cập nhật cấu hình khi người dùng đổi ở Sidebar
        st.session_state["facade"].llm_client = MultiLLMClient(
            provider=config["provider"],
            api_key=config["api_key"],
            model_name=config["model_name"]
        )
        st.session_state["facade"].classifier.confidence_threshold = config["confidence_threshold"]
        st.session_state["facade"].classifier.force_llm_mode = config["force_llm"]

    if "raw_input_text" not in st.session_state:
        st.session_state["raw_input_text"] = ""
    if "analysis_result" not in st.session_state:
        st.session_state["analysis_result"] = None

    # 3. Khu vực Nhập liệu Đầu vào
    with st.container():
        input_col1, input_col2 = st.columns([3, 2])

        with input_col1:
            uploaded_file = st.file_uploader(
                "Tải lên tài liệu mô tả bài toán (.docx, .txt)",
                type=["docx", "txt"],
                help="Hỗ trợ tài liệu tiếng Việt và tiếng Anh có bảng biểu, giới hạn tối đa 25 MB."
            )

        with input_col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("⚡ Nạp Tài liệu Mẫu E-Commerce (1-Click)", use_container_width=True):
                sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_ecommerce_vi.txt")
                if os.path.exists(sample_path):
                    with open(sample_path, "r", encoding="utf-8") as f:
                        st.session_state["raw_input_text"] = f.read()
                    st.rerun()

        text_input = st.text_area(
            "Hoặc dán trực tiếp đoạn văn bản mô tả nghiệp vụ thô vào đây:",
            value=st.session_state["raw_input_text"],
            height=130,
            placeholder="Ví dụ: Hệ thống cho phép khách hàng đăng nhập bằng số điện thoại. Thời gian phản hồi phải cực nhanh và thân thiện..."
        )

        btn_run = st.button("🚀 Bắt đầu Phân tích Yêu cầu", type="primary", use_container_width=True)

    # 4. Thực thi Phân tích
    if btn_run:
        facade: RequirementAnalysisFacade = st.session_state["facade"]

        if uploaded_file is not None:
            source = uploaded_file.getvalue()
            filename = uploaded_file.name
            size_bytes = len(source)
        elif text_input.strip():
            source = text_input.strip()
            filename = "pasted_text.txt"
            size_bytes = len(source.encode("utf-8"))
        else:
            st.warning("⚠️ Vui lòng tải lên tệp (.docx / .txt) hoặc dán văn bản nghiệp vụ trước khi bấm Phân tích.")
            return

        with st.spinner("Đang xử lý phân tích 6 bước (Đọc tệp -> Phân loại -> Bắt lỗi mơ hồ -> Sinh User Story -> Kết xuất SRS)..."):
            try:
                result = facade.analyze_document(
                    source=source,
                    filename=filename,
                    file_size_bytes=size_bytes
                )
                st.session_state["analysis_result"] = result
                st.success(f"✅ Hoàn tất phân tích {len(result.requirements)} yêu cầu trong {result.timings.get('total_execution_sec', 0.0)} giây!")
            except Exception as e:
                st.error(f"❌ Đã xảy ra lỗi trong quá trình xử lý: {str(e)}")

    # 5. Hiển thị Bàn làm việc (Workbench) khi đã có kết quả
    if st.session_state["analysis_result"] is not None:
        st.markdown("---")
        render_workbench(st.session_state["facade"], st.session_state["analysis_result"])


if __name__ == "__main__":
    main()
