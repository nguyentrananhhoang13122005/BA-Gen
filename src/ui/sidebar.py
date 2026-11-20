"""Thanh cài đặt bên trái (Sidebar) thân thiện, rõ ràng cho mọi đối tượng người dùng.

Giải thích minh bạch cơ chế hoạt động khi có API Key (dùng AI thông minh)
và khi chưa có API Key (tự động chuyển sang bộ học máy & quy tắc có sẵn).
"""

import os
import streamlit as st
from src.ui.design_system import render_html, svg_icon


def render_sidebar() -> dict:
    """Render thanh cài đặt bên trái và trả về cấu hình."""
    with st.sidebar:
        render_html(
            f"""
<div style="display: flex; align-items: center; gap: 10px; padding-bottom: 10px;
            border-bottom: 1px solid #E2E8F0; margin-bottom: 14px;">
    <span style="color: #1E40AF;">{svg_icon("sliders")}</span>
    <div>
        <div style="font-weight: 700; font-size: 1rem; color: #0F172A; line-height: 1.2;">
            Cài đặt Chế độ Phân tích
        </div>
        <div style="font-size: 0.78rem; color: #64748B;">
            Chọn AI trực tuyến hoặc Chế độ có sẵn
        </div>
    </div>
</div>
            """
        )

    providers = [
        "Groq AI (Tốc độ nhanh - Khuyên dùng)",
        "Google Gemini AI",
        "OpenRouter AI (Đa mô hình)",
        "Ollama (Chạy AI trên máy cá nhân)",
        "Chế độ Có sẵn (Offline - Không cần API Key)",
    ]
    selected_provider_raw = st.sidebar.selectbox(
        "1. Chọn bộ xử lý ngôn ngữ:",
        providers,
        index=0,
    )

    provider_map = {
        "Groq AI (Tốc độ nhanh - Khuyên dùng)": "groq",
        "Google Gemini AI": "gemini",
        "OpenRouter AI (Đa mô hình)": "openrouter",
        "Ollama (Chạy AI trên máy cá nhân)": "ollama",
        "Chế độ Có sẵn (Offline - Không cần API Key)": "offline",
    }
    provider = provider_map[selected_provider_raw]

    api_key = ""
    model_name = ""

    if provider == "groq":
        default_key = os.getenv("GROQ_API_KEY", "")
        api_key = st.sidebar.text_input(
            "2. Nhập Groq API Key:",
            value=default_key,
            type="password",
            placeholder="Dán mã gsk_... vào đây",
        )
        model_name = "llama-3.3-70b-versatile"
    elif provider == "gemini":
        default_key = os.getenv("GEMINI_API_KEY", "")
        api_key = st.sidebar.text_input(
            "2. Nhập Google Gemini API Key:",
            value=default_key,
            type="password",
            placeholder="Dán mã AIza... vào đây",
        )
        model_name = "gemini-1.5-flash"
    elif provider == "openrouter":
        default_key = os.getenv("OPENROUTER_API_KEY", "")
        api_key = st.sidebar.text_input(
            "2. Nhập OpenRouter API Key:",
            value=default_key,
            type="password",
            placeholder="Dán mã sk-or-... vào đây",
        )
        model_name = "meta-llama/llama-3.3-70b-instruct:free"
    elif provider == "ollama":
        model_name = st.sidebar.text_input("2. Tên mô hình Ollama trên máy:", value="llama3")
        api_key = "local_ollama"

    # Hiển thị trạng thái rõ ràng cho người dùng biết tại sao không có key vẫn chạy được
    has_valid_key = (provider == "ollama") or (provider != "offline" and len(api_key.strip()) > 5)

    with st.sidebar:
        if provider == "offline":
            render_html(
                """
<div style="background: #EFF6FF; border: 1px solid #BFDBFE; color: #1E40AF;
            padding: 10px 12px; border-radius: 8px; font-size: 0.83rem; margin-top: 6px; line-height: 1.5;">
    <b>Đang dùng Bộ phân tích có sẵn:</b><br>
    Hệ thống sử dụng mô hình Học máy nội bộ và Từ điển mẫu tiếng Việt/Anh có sẵn trong máy.
    Bạn có thể bấm phân tích ngay mà <b>không cần nhập API Key</b>.
</div>
                """
            )
        elif has_valid_key:
            render_html(
                """
<div style="background: #F0FDF4; border: 1px solid #86EFAC; color: #166534;
            padding: 10px 12px; border-radius: 8px; font-size: 0.83rem; margin-top: 6px; line-height: 1.5;">
    <b>Đã nhận API Key hợp lệ:</b><br>
    Hệ thống sẽ kết nối trực tiếp với AI để phân tích sâu và viết lại câu thông minh.
</div>
                """
            )
        else:
            render_html(
                """
<div style="background: #FFFBEB; border: 1px solid #FCD34D; color: #92400E;
            padding: 10px 12px; border-radius: 8px; font-size: 0.83rem; margin-top: 6px; line-height: 1.5;">
    <b>Bạn chưa nhập API Key:</b><br>
    • Nếu để trống và bấm Phân tích, hệ thống sẽ <b>tự động chuyển sang Bộ học máy có sẵn (Offline)</b>
      để bạn vẫn trải nghiệm thử được ngay.<br>
    • Nếu muốn AI phân tích thông minh nhất, hãy dán API Key vào ô phía trên.
</div>
                """
            )

    require_key = False
    if provider not in ("offline", "ollama"):
        require_key = st.sidebar.checkbox(
            "Bắt buộc phải nhập API Key mới cho chạy",
            value=False,
            help="Bật tùy chọn này nếu bạn không muốn hệ thống tự động chuyển sang chế độ Offline khi quên nhập API Key.",
        )

    # Ẩn các tham số kỹ thuật chuyên sâu vào hộp mở rộng để giao diện gọn gàng
    with st.sidebar.expander("Cài đặt nâng cao (Dành cho Kỹ thuật)", expanded=False):
        if provider in ("groq", "gemini", "openrouter"):
            model_name = st.text_input("Tên Model tùy chỉnh:", value=model_name)
        conf_threshold = st.slider(
            "Ngưỡng độ chắc chắn chuyển sang AI",
            min_value=0.50,
            max_value=0.95,
            value=0.75,
            step=0.05,
            help="Khi mô hình máy học nội bộ dự đoán dưới mức này, câu đó sẽ được gửi lên AI xử lý.",
        )
        force_llm = st.checkbox(
            "Gửi 100% câu lên AI xử lý",
            value=True if has_valid_key else False,
            disabled=(not has_valid_key),
        )

    return {
        "provider": provider,
        "api_key": api_key,
        "model_name": model_name,
        "confidence_threshold": conf_threshold,
        "force_llm": force_llm,
        "require_key": require_key,
        "has_valid_key": has_valid_key,
    }
