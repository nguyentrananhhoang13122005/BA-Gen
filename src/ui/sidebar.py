"""Thành phần thanh điều hướng Sidebar cho giao diện Streamlit.

Cho phép cấu hình Cổng LLM (Groq, OpenRouter, Gemini, Offline ML),
nhập khóa API bảo mật (type='password'), chọn ngưỡng tin cậy và tải tệp.
"""

import os
import streamlit as st


def render_sidebar() -> dict:
    """Render thanh bên và trả về từ điển cấu hình người dùng."""
    st.sidebar.title("🛠️ Cấu hình Hệ thống")

    # 1. Chọn Provider
    providers = [
        "Groq (Tốc độ cao - Khuyến nghị)",
        "OpenRouter (Nhiều Model Miễn phí)",
        "Gemini (Google AI)",
        "Ollama (Cục bộ)",
        "Offline ML (TF-IDF + LinearSVC)"
    ]
    selected_provider_raw = st.sidebar.selectbox("Cổng AI / Mô hình", providers, index=0)

    provider_map = {
        "Groq (Tốc độ cao - Khuyến nghị)": "groq",
        "OpenRouter (Nhiều Model Miễn phí)": "openrouter",
        "Gemini (Google AI)": "gemini",
        "Ollama (Cục bộ)": "ollama",
        "Offline ML (TF-IDF + LinearSVC)": "offline"
    }
    provider = provider_map[selected_provider_raw]

    # 2. Khóa API (Tự động nạp từ .env nếu có)
    api_key = ""
    model_name = ""

    if provider == "groq":
        default_key = os.getenv("GROQ_API_KEY", "")
        api_key = st.sidebar.text_input("Groq API Key", value=default_key, type="password")
        model_name = st.sidebar.text_input("Model Name", value="llama-3.3-70b-versatile")
    elif provider == "openrouter":
        default_key = os.getenv("OPENROUTER_API_KEY", "")
        api_key = st.sidebar.text_input("OpenRouter API Key", value=default_key, type="password")
        model_name = st.sidebar.text_input("Model Name", value="meta-llama/llama-3.3-70b-instruct:free")
    elif provider == "gemini":
        default_key = os.getenv("GEMINI_API_KEY", "")
        api_key = st.sidebar.text_input("Gemini API Key", value=default_key, type="password")
        model_name = st.sidebar.text_input("Model Name", value="gemini-1.5-flash")
    elif provider == "ollama":
        model_name = st.sidebar.text_input("Ollama Model", value="llama3")
        api_key = "local_ollama"
    else:
        st.sidebar.info("💡 Chế độ Ngoại tuyến: Hoạt động 100% không cần mạng và API Key.")

    # 3. Ngưỡng tin cậy (Confidence Threshold)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Định tuyến Thông minh")
    conf_threshold = st.sidebar.slider(
        "Ngưỡng tin cậy kích hoạt LLM",
        min_value=0.50,
        max_value=0.95,
        value=0.75,
        step=0.05,
        help="Các câu phân loại bởi LinearSVC có độ tin cậy thấp hơn ngưỡng này sẽ được định tuyến sang LLM để phân xử."
    )

    force_llm = st.sidebar.checkbox(
        "Ép buộc dùng LLM cho 100% câu",
        value=False,
        disabled=(provider == "offline")
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("BA-Gen (ReqAssist-NLP) v1.0.0 — Chuẩn IEEE 830 & ISO 25010")

    return {
        "provider": provider,
        "api_key": api_key,
        "model_name": model_name,
        "confidence_threshold": conf_threshold,
        "force_llm": force_llm,
    }
