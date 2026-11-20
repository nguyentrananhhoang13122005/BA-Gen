"""Thanh cài đặt Kết nối AI (Sidebar) cho BA-Gen.

Chỉ sử dụng kết nối AI thực tế (Groq, Google Gemini, OpenRouter, Ollama)
với kiểm tra khóa API nghiêm ngặt, loại bỏ hoàn toàn mock/offline mode.
"""

import os
import streamlit as st
from src.classifiers.llm_client import is_real_api_key
from src.ui.design_system import render_html, svg_icon


def render_sidebar() -> dict:
    """Render thanh cài đặt kết nối AI thực tế bên trái và trả về cấu hình."""
    with st.sidebar:
        render_html(
            f"""
<div style="display: flex; align-items: center; gap: 10px; padding-bottom: 10px;
            border-bottom: 1px solid #E2E8F0; margin-bottom: 14px;">
    <span style="color: #1E40AF;">{svg_icon("sliders")}</span>
    <div>
        <div style="font-weight: 700; font-size: 1rem; color: #0F172A; line-height: 1.2;">
            Kết nối Mô hình AI
        </div>
        <div style="font-size: 0.78rem; color: #64748B;">
            Cấu hình API Key để phân tích dữ liệu thật
        </div>
    </div>
</div>
            """
        )

    providers = [
        "Groq AI (Llama 3.3 70B - Tốc độ cao)",
        "Google Gemini AI (Gemini 1.5 Flash)",
        "OpenRouter AI (Đa mô hình)",
        "Ollama (Local AI Server)",
    ]
    selected_provider_raw = st.sidebar.selectbox(
        "1. Chọn nhà cung cấp AI:",
        providers,
        index=0,
    )

    provider_map = {
        "Groq AI (Llama 3.3 70B - Tốc độ cao)": "groq",
        "Google Gemini AI (Gemini 1.5 Flash)": "gemini",
        "OpenRouter AI (Đa mô hình)": "openrouter",
        "Ollama (Local AI Server)": "ollama",
    }
    provider = provider_map[selected_provider_raw]

    api_key = ""
    model_name = ""

    if provider == "groq":
        env_key = os.getenv("GROQ_API_KEY", "")
        default_key = env_key if is_real_api_key(env_key) else ""
        api_key = st.sidebar.text_input(
            "2. Nhập Groq API Key:",
            value=default_key,
            type="password",
            placeholder="Dán khóa gsk_... thực tế vào đây",
        )
        model_name = "llama-3.3-70b-versatile"
    elif provider == "gemini":
        env_key = os.getenv("GEMINI_API_KEY", "")
        default_key = env_key if is_real_api_key(env_key) else ""
        api_key = st.sidebar.text_input(
            "2. Nhập Google Gemini API Key:",
            value=default_key,
            type="password",
            placeholder="Dán khóa AIza... thực tế vào đây",
        )
        model_name = "gemini-1.5-flash"
    elif provider == "openrouter":
        env_key = os.getenv("OPENROUTER_API_KEY", "")
        default_key = env_key if is_real_api_key(env_key) else ""
        api_key = st.sidebar.text_input(
            "2. Nhập OpenRouter API Key:",
            value=default_key,
            type="password",
            placeholder="Dán khóa sk-or-... thực tế vào đây",
        )
        model_name = "meta-llama/llama-3.3-70b-instruct:free"
    elif provider == "ollama":
        model_name = st.sidebar.text_input("2. Tên mô hình Ollama đang chạy:", value="llama3")
        api_key = "local_ollama"

    has_valid_key = (provider == "ollama") or is_real_api_key(api_key)

    with st.sidebar:
        if has_valid_key:
            render_html(
                """
<div style="background: #F0FDF4; border: 1px solid #86EFAC; color: #166534;
            padding: 10px 12px; border-radius: 8px; font-size: 0.83rem; margin-top: 6px; line-height: 1.5;">
    <b>Đã nhập khóa API:</b><br>
    Hệ thống đã sẵn sàng gửi tài liệu thực tế của bạn lên AI để bóc tách yêu cầu,
    sửa câu mơ hồ và sinh kịch bản.
</div>
                """
            )
        else:
            render_html(
                """
<div style="background: #FEF2F2; border: 1px solid #FCA5A5; color: #991B1B;
            padding: 10px 12px; border-radius: 8px; font-size: 0.83rem; margin-top: 6px; line-height: 1.5;">
    <b>Chưa có API Key:</b><br>
    Vui lòng nhập API Key thực tế vào ô phía trên trước khi bấm Phân tích.
    Hệ thống chỉ xử lý trên dữ liệu thật qua kết nối AI thực tế.
</div>
                """
            )

    with st.sidebar.expander("Tùy chỉnh Model nâng cao", expanded=False):
        if provider in ("groq", "gemini", "openrouter"):
            model_name = st.text_input("Tên Model AI:", value=model_name)
        conf_threshold = st.slider(
            "Ngưỡng độ tin cậy định tuyến:",
            min_value=0.50,
            max_value=0.95,
            value=0.75,
            step=0.05,
        )

    return {
        "provider": provider,
        "api_key": api_key.strip() if api_key else "",
        "model_name": model_name,
        "confidence_threshold": conf_threshold,
        "force_llm": True,
        "require_key": True,
        "has_valid_key": has_valid_key,
    }
