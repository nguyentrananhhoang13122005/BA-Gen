"""Hệ thống Thiết kế Giao diện (UI/UX Design System) cho BA-Gen.

Thiết kế theo hướng trực quan, hiện đại, thân thiện với cả người không chuyên
(non-tech/business) lẫn kỹ sư phần mềm (BA/Dev):
- Hàm `render_html` chuẩn hóa toàn bộ chuỗi HTML trước khi đẩy vào Streamlit,
  triệt tiêu 100% lỗi Markdown hiểu nhầm dòng thụt lề 4 dấu cách thành khối code.
- Hệ thống biểu tượng Vector SVG sắc nét, bảng màu tương phản cao, dễ đọc.
- Hiệu ứng chuyển động (Animation) trực quan theo từng bước xử lý ngôn ngữ.
"""

import streamlit as st


SVG_ICONS = {
    "blueprint": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18" rx="3"/><line x1="3" y1="9" x2="21" y2="9"/>'
        '<line x1="9" y1="21" x2="9" y2="9"/></svg>'
    ),
    "cpu": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>'
        '<path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/></svg>'
    ),
    "layers": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/>'
        '<polyline points="2 12 12 17 22 12"/></svg>'
    ),
    "shield": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>'
    ),
    "alert": (
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.0" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
    ),
    "check": (
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="20 6 9 17 4 12"/></svg>'
    ),
    "sparkles": (
        '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21'
        'l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>'
    ),
    "git-branch": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/>'
        '<circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>'
    ),
    "file-text": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
        '<polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>'
        '<line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>'
    ),
    "bar-chart": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/>'
        '<line x1="6" y1="20" x2="6" y2="16"/></svg>'
    ),
    "sliders": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
        '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
        '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
        '<line x1="17" y1="16" x2="23" y2="16"/></svg>'
    ),
    "clock": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
    ),
    "share": (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
        '<line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>'
        '<line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>'
    ),
    "user": (
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
    ),
}


def svg_icon(name: str) -> str:
    """Trả về chuỗi SVG inline theo tên."""
    return SVG_ICONS.get(name, SVG_ICONS["blueprint"])


def clean_html(raw_html: str) -> str:
    """Loại bỏ toàn bộ khoảng trắng đầu dòng để Markdown không biến HTML thành code block."""
    return "\n".join(line.strip() for line in raw_html.splitlines() if line.strip())


def render_html(raw_html: str, slot=None):
    """Render HTML an toàn tuyệt đối trong Streamlit không bị lỗi lộ thẻ HTML."""
    target = slot if slot is not None else st
    target.markdown(clean_html(raw_html), unsafe_allow_html=True)


def is_llm_ready(config: dict) -> bool:
    """Kiểm tra xem người dùng đã thực sự cấu hình API Key hợp lệ cho AI hay chưa."""
    provider = config.get("provider", "offline")
    if provider == "offline":
        return False
    if provider == "ollama":
        return True
    api_key = (config.get("api_key") or "").strip()
    return len(api_key) > 5


def inject_design_system_css():
    """Tiêm hệ thống CSS hiện đại, rõ ràng, có hiệu ứng chuyển động mượt mà."""
    css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --font-sans: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono: 'JetBrains Mono', Consolas, monospace;

    --bg-canvas: #F4F6FB;
    --bg-surface: #FFFFFF;
    --bg-subtle: #F8FAFC;
    --bg-navy: #0F172A;

    --ink-primary: #0F172A;
    --ink-secondary: #334155;
    --ink-muted: #64748B;

    --border-light: #E2E8F0;
    --border-hover: #94A3B8;
    --primary-blue: #1E40AF;
    --primary-blue-light: #EFF6FF;

    --fr-text: #0F766E;
    --fr-bg: #F0FDFA;
    --fr-border: #99F6E4;

    --nfr-text: #1D4ED8;
    --nfr-bg: #EFF6FF;
    --nfr-border: #BFDBFE;

    --warn-text: #92400E;
    --warn-bg: #FFFBEB;
    --warn-border: #FCD34D;

    --ok-text: #166534;
    --ok-bg: #F0FDF4;
    --ok-border: #86EFAC;

    --danger-text: #B91C1C;
    --danger-bg: #FEF2F2;
    --danger-border: #FCA5A5;

    --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.05);
    --shadow-md: 0 8px 20px -4px rgba(15, 23, 42, 0.08);
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

html, body, [class*="css"] {
    font-family: var(--font-sans) !important;
    color: var(--ink-primary);
}

.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1380px !important;
}

@keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); }
    70% { box-shadow: 0 0 0 9px rgba(37, 99, 235, 0); }
    100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
}

@keyframes progressWave {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

@keyframes fadeInSlide {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes fillMeter {
    from { transform: scaleX(0); }
    to { transform: scaleX(1); }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}

/* 1. BANNER ĐẦU TRANG */
.hero-shell {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
    color: #FFFFFF;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    box-shadow: var(--shadow-md);
}

.hero-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.hero-icon-box {
    width: 48px;
    height: 48px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.22);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #93C5FD;
    flex-shrink: 0;
}

.hero-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0;
    line-height: 1.25;
}

.hero-desc {
    font-size: 0.9rem;
    color: #CBD5E1;
    margin: 4px 0 0 0;
}

.status-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
}

.status-pill {
    font-size: 0.8rem;
    font-weight: 500;
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: #F8FAFC;
    padding: 6px 12px;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    gap: 7px;
}

.dot-green {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #4ADE80;
    display: inline-block;
}

.dot-amber {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #FBBF24;
    display: inline-block;
}

/* 2. THANH TIẾN TRÌNH 6 BƯỚC XỬ LÝ (ANIMATED PIPELINE) */
.pipeline-box {
    background: var(--bg-surface);
    border: 1px solid var(--border-light);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 18px;
    box-shadow: var(--shadow-sm);
}

.pipeline-header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border-light);
}

.pipeline-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--ink-primary);
    display: flex;
    align-items: center;
    gap: 8px;
}

.pipeline-sub {
    font-size: 0.82rem;
    color: var(--ink-muted);
}

.pipeline-steps-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 10px;
}

@media (max-width: 992px) {
    .pipeline-steps-grid { grid-template-columns: repeat(2, 1fr); }
}

.step-card {
    background: var(--bg-subtle);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 10px 12px;
    transition: all 0.25s var(--ease-out);
}

.step-card.is-running {
    background: #EFF6FF;
    border-color: #2563EB;
    animation: pulseGlow 1.6s infinite;
}

.step-card.is-completed {
    background: #F0FDF4;
    border-color: #86EFAC;
}

.step-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--ink-muted);
    margin-bottom: 4px;
}

.step-card.is-running .step-top { color: #1D4ED8; }
.step-card.is-completed .step-top { color: #15803D; }

.step-name {
    font-size: 0.83rem;
    font-weight: 600;
    color: var(--ink-primary);
    line-height: 1.3;
}

.pipeline-wave {
    height: 4px;
    width: 100%;
    border-radius: 2px;
    margin-top: 12px;
    background: linear-gradient(90deg, #E2E8F0 0%, #2563EB 50%, #E2E8F0 100%);
    background-size: 200% 100%;
    animation: progressWave 1.4s linear infinite;
}

/* 3. DẢI 5 THẺ TỔNG QUAN DỄ HIỂU (KPI CARDS) */
.summary-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}

@media (max-width: 992px) {
    .summary-grid { grid-template-columns: repeat(2, 1fr); }
}

.summary-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-light);
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: var(--shadow-sm);
    animation: fadeInSlide 0.35s var(--ease-out) both;
}

.summary-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}

.summary-label {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--ink-secondary);
}

.summary-number {
    font-size: 1.65rem;
    font-weight: 700;
    color: var(--ink-primary);
    line-height: 1.15;
}

.summary-explain {
    font-size: 0.77rem;
    color: var(--ink-muted);
    margin-top: 4px;
    line-height: 1.35;
}

.meter-bg {
    height: 5px;
    background: #E2E8F0;
    border-radius: 3px;
    margin-top: 10px;
    overflow: hidden;
}

.meter-bar {
    height: 100%;
    border-radius: 3px;
    transform-origin: left;
    animation: fillMeter 0.65s var(--ease-out) both;
}

/* 4. THẺ CHI TIẾT YÊU CẦU (REQUIREMENT CARDS) */
.req-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-light);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: var(--shadow-sm);
    animation: fadeInSlide 0.3s var(--ease-out) both;
    transition: border-color 0.2s var(--ease-out), box-shadow 0.2s var(--ease-out);
}

.req-card:hover {
    border-color: var(--border-hover);
    box-shadow: var(--shadow-md);
}

.req-header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding-bottom: 10px;
    margin-bottom: 10px;
    border-bottom: 1px solid var(--border-light);
}

.badge-id {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-weight: 700;
    background: #0F172A;
    color: #FFFFFF;
    padding: 4px 10px;
    border-radius: 6px;
}

.badge-fr {
    font-size: 0.8rem;
    font-weight: 600;
    background: var(--fr-bg);
    color: var(--fr-text);
    border: 1px solid var(--fr-border);
    padding: 4px 10px;
    border-radius: 6px;
}

.badge-nfr {
    font-size: 0.8rem;
    font-weight: 600;
    background: var(--nfr-bg);
    color: var(--nfr-text);
    border: 1px solid var(--nfr-border);
    padding: 4px 10px;
    border-radius: 6px;
}

.badge-sub {
    font-size: 0.78rem;
    font-weight: 500;
    background: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
    padding: 3px 10px;
    border-radius: 6px;
}

.badge-ok {
    font-size: 0.78rem;
    font-weight: 600;
    background: var(--ok-bg);
    color: var(--ok-text);
    border: 1px solid var(--ok-border);
    padding: 3px 10px;
    border-radius: 6px;
}

.badge-warn {
    font-size: 0.78rem;
    font-weight: 600;
    background: var(--warn-bg);
    color: var(--warn-text);
    border: 1px solid var(--warn-border);
    padding: 3px 10px;
    border-radius: 6px;
}

.req-content {
    font-size: 1rem;
    line-height: 1.65;
    color: var(--ink-primary);
    margin: 6px 0 10px 0;
}

.vague-word {
    background: var(--danger-bg);
    color: var(--danger-text);
    border: 1px solid var(--danger-border);
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 5px;
}

.issue-explain-box {
    background: var(--warn-bg);
    color: var(--warn-text);
    border: 1px solid var(--warn-border);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.88rem;
    margin-top: 8px;
    line-height: 1.5;
}

.smart-suggest-box {
    background: var(--ok-bg);
    color: var(--ok-text);
    border: 1px solid var(--ok-border);
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 0.92rem;
    margin-top: 8px;
    line-height: 1.55;
}

/* 5. THẺ KỊCH BẢN NGƯỜI DÙNG (USER STORY CARDS) */
.us-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-light);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: var(--shadow-sm);
    animation: fadeInSlide 0.3s var(--ease-out) both;
}

.us-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 12px 0;
}

@media (max-width: 768px) {
    .us-grid { grid-template-columns: 1fr; }
}

.us-box {
    background: var(--bg-subtle);
    border: 1px solid var(--border-light);
    border-radius: 8px;
    padding: 12px 14px;
}

.us-box-title {
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--primary-blue);
    margin-bottom: 4px;
}

.us-box-value {
    font-size: 0.93rem;
    font-weight: 500;
    color: var(--ink-primary);
    line-height: 1.45;
}

.test-scenario-box {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 12px 16px;
    margin-top: 10px;
    font-size: 0.88rem;
    line-height: 1.65;
}

.test-scenario-header {
    font-weight: 700;
    color: #1E3A8A;
    margin-bottom: 6px;
    padding-bottom: 4px;
    border-bottom: 1px solid #E2E8F0;
}

.tag-given {
    display: inline-block;
    min-width: 135px;
    font-weight: 700;
    color: #0369A1;
}
.tag-when {
    display: inline-block;
    min-width: 135px;
    font-weight: 700;
    color: #B45309;
}
.tag-then {
    display: inline-block;
    min-width: 135px;
    font-weight: 700;
    color: #15803D;
}

/* 6. BẢNG MA TRẬN KIỂM CHUẨN */
.cm-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    margin-top: 10px;
}
.cm-table th, .cm-table td {
    border: 1px solid var(--border-light);
    padding: 8px 10px;
    text-align: center;
}
.cm-table th {
    background: var(--bg-subtle);
    color: var(--ink-secondary);
    font-weight: 600;
}
.cm-good { background: #F0FDF4; color: #166534; font-weight: 700; }
.cm-miss { background: #FEF2F2; color: #991B1B; }

div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 10px 16px !important;
}
</style>
    """
    render_html(css)


def render_command_header(config: dict, project_lang: str = "vi"):
    """Render Banner đầu trang dễ hiểu, hiển thị trung thực trạng thái kết nối AI / Offline."""
    provider = config.get("provider", "offline")
    llm_ready = is_llm_ready(config)

    provider_names = {
        "groq": "Groq AI",
        "openrouter": "OpenRouter AI",
        "gemini": "Google Gemini AI",
        "ollama": "Ollama (Nội bộ)",
        "offline": "Học máy có sẵn (Offline)",
    }
    p_display = provider_names.get(provider, provider.upper())

    if llm_ready:
        dot_cls = "dot-green"
        engine_status = f"Đang bật AI: {p_display}"
    elif provider == "offline":
        dot_cls = "dot-amber"
        engine_status = "Chế độ Học máy có sẵn (Không cần API Key)"
    else:
        dot_cls = "dot-amber"
        engine_status = f"Chưa nhập API Key {p_display} → Tự động dùng Chế độ có sẵn (Offline)"

    lang_display = "Tiếng Việt" if project_lang == "vi" else "Tiếng Anh"

    header_html = f"""
<div class="hero-shell">
    <div class="hero-left">
        <div class="hero-icon-box">{svg_icon("blueprint")}</div>
        <div>
            <h1 class="hero-title">BA-Gen — Trợ lý Phân tích Yêu cầu &amp; Viết Đặc tả Phần mềm</h1>
            <p class="hero-desc">
                Biến văn bản mô tả ý tưởng thô thành Danh sách Tính năng rõ ràng, Kịch bản Người dùng,
                Sơ đồ Chức năng và Tài liệu Word (.docx)
            </p>
        </div>
    </div>
    <div class="status-badge-row">
        <span class="status-pill">
            <span class="{dot_cls}"></span>
            <span>{engine_status}</span>
        </span>
        <span class="status-pill">Ngôn ngữ: {lang_display}</span>
    </div>
</div>
    """
    render_html(header_html)


PIPELINE_STAGES = [
    ("Bước 1", "Đọc & Tách từng câu", "parsing_and_segmentation_sec"),
    ("Bước 2", "Phân loại Tính năng", "classification_sec"),
    ("Bước 3", "Tìm & Sửa câu mơ hồ", "ambiguity_and_smart_sec"),
    ("Bước 4", "Viết kịch bản người dùng", "user_stories_gen_sec"),
    ("Bước 5", "Vẽ sơ đồ chức năng", "plantuml_export_sec"),
    ("Bước 6", "Đóng gói file Báo cáo", "total_execution_sec"),
]


def build_pipeline_console_html(
    active_step: int,
    status_title: str,
    status_detail: str,
    timings: dict = None,
    is_running: bool = True,
) -> str:
    """Tạo giao diện thanh tiến trình 6 bước thân thiện với người dùng."""
    timings = timings or {}
    nodes_html = []

    for idx, (step_label, name, timing_key) in enumerate(PIPELINE_STAGES, start=1):
        if is_running:
            if idx < active_step:
                state_cls = "is-completed"
                state_tag = "Hoàn thành"
            elif idx == active_step:
                state_cls = "is-running"
                state_tag = "Đang xử lý..."
            else:
                state_cls = ""
                state_tag = "Đang chờ"
            time_str = state_tag
        else:
            state_cls = "is-completed"
            sec_val = timings.get(timing_key, 0.0)
            time_str = f"Xong ({sec_val:.2f}s)"

        nodes_html.append(
            f'<div class="step-card {state_cls}">'
            f'<div class="step-top"><span>{step_label}</span><span>{time_str}</span></div>'
            f'<div class="step-name">{name}</div>'
            f'</div>'
        )

    wave_bar = '<div class="pipeline-wave"></div>' if is_running else ""

    raw = f"""
<div class="pipeline-box">
    <div class="pipeline-header">
        <div class="pipeline-title">{svg_icon("cpu")} <span>{status_title}</span></div>
        <div class="pipeline-sub">{status_detail}</div>
    </div>
    <div class="pipeline-steps-grid">{"".join(nodes_html)}</div>
    {wave_bar}
</div>
    """
    return clean_html(raw)


def render_empty_state_blueprint():
    """Hiển thị hướng dẫn 3 bước trực quan, dễ hiểu cho người mới bắt đầu."""
    guide_html = f"""
<div style="margin-top: 10px;">
    <div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-bottom: 12px;">
        Cách sử dụng công cụ chỉ với 3 bước đơn giản:
    </div>
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
        <div class="req-card" style="margin-bottom: 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; color: #1E40AF;">
                {svg_icon("file-text")}
                <span style="font-size: 0.82rem; font-weight: 700;">BƯỚC 1 · NHẬP Ý TƯỞNG / ĐỀ BÀI</span>
            </div>
            <div style="font-weight: 700; font-size: 1rem; margin-bottom: 6px;">
                Dán văn bản hoặc tải file Word (.docx)
            </div>
            <p style="font-size: 0.88rem; color: #475569; line-height: 1.55; margin: 0;">
                Bạn chỉ cần dán đoạn mô tả mong muốn về phần mềm (hoặc bấm nút
                <b>"Dùng thử Bài mẫu Thương mại điện tử"</b> ở trên để xem ngay cách hệ thống hoạt động).
            </p>
        </div>
        <div class="req-card" style="margin-bottom: 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; color: #0F766E;">
                {svg_icon("sparkles")}
                <span style="font-size: 0.82rem; font-weight: 700;">BƯỚC 2 · TỰ ĐỘNG RÀ SOÁT &amp; LÀM RÕ</span>
            </div>
            <div style="font-weight: 700; font-size: 1rem; margin-bottom: 6px;">
                Phát hiện từ viết chung chung &amp; gợi ý sửa
            </div>
            <p style="font-size: 0.88rem; color: #475569; line-height: 1.55; margin: 0;">
                Hệ thống tự động tách văn bản thành từng yêu cầu nhỏ, chỉ ra những chỗ viết còn cảm tính
                (như <i>"chạy nhanh", "dễ dùng"</i>) và gợi ý câu viết lại rõ ràng, có con số cụ thể.
            </p>
        </div>
        <div class="req-card" style="margin-bottom: 0;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; color: #1D4ED8;">
                {svg_icon("git-branch")}
                <span style="font-size: 0.82rem; font-weight: 700;">BƯỚC 3 · XUẤT BÁO CÁO &amp; SƠ ĐỒ</span>
            </div>
            <div style="font-weight: 700; font-size: 1rem; margin-bottom: 6px;">
                Tải file Word (.docx), Sơ đồ &amp; đẩy sang Jira
            </div>
            <p style="font-size: 0.88rem; color: #475569; line-height: 1.55; margin: 0;">
                Nhận ngay danh sách kịch bản người dùng, sơ đồ chức năng trực quan và tải về tài liệu
                đặc tả phần mềm (.docx) hoàn chỉnh hoặc đồng bộ sang Jira, GitHub, Trello.
            </p>
        </div>
    </div>
</div>
    """
    render_html(guide_html)
