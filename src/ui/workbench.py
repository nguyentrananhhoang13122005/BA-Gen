"""Bàn làm việc Kết quả Phân tích (Workbench) thân thiện, trực quan và dễ hiểu.

Sử dụng `render_html` chuẩn hóa toàn bộ giao diện thẻ HTML (không bao giờ bị lỗi
lộ mã HTML trên Streamlit) và diễn giải mọi thuật ngữ kỹ thuật bằng tiếng Việt
tự nhiên để cả người không chuyên lẫn BA chuyên nghiệp đều nắm bắt ngay.
"""

import html
import re
import streamlit as st
from src.classifiers.evaluate_benchmark import BenchmarkEvaluator
from src.core.facade import RequirementAnalysisFacade
from src.core.models import AnalysisResultDTO
from src.ui.design_system import build_pipeline_console_html, render_html, svg_icon


ISO_VI_LABELS = {
    "Performance": "Hiệu năng & Tốc độ",
    "Security": "Bảo mật & An toàn",
    "Usability": "Dễ sử dụng & Trải nghiệm",
    "Reliability": "Độ ổn định & Tin cậy",
    "Maintainability": "Dễ bảo trì & Nâng cấp",
    "Portability": "Tương thích đa nền tảng",
}

ISO_CATEGORIES = list(ISO_VI_LABELS.keys())


def highlight_vague_terms(text: str, vague_terms: list) -> str:
    """Tô nổi bật các từ viết chung chung, cảm tính trong câu yêu cầu."""
    escaped_text = html.escape(text)
    replacement = r'<span class="vague-word" title="Từ viết chung chung, cần thay bằng con số cụ thể">\1</span>'
    for term in sorted(vague_terms, key=len, reverse=True):
        escaped_term = html.escape(term)
        pattern = re.compile(rf"(?<!\w)({re.escape(escaped_term)})(?!\w)", re.IGNORECASE)
        escaped_text = pattern.sub(replacement, escaped_text)
    return escaped_text


def _render_summary_cards(result: AnalysisResultDTO):
    """Hiển thị 5 thẻ tóm tắt kết quả bằng ngôn ngữ đời thường, dễ hiểu."""
    total_reqs = max(len(result.requirements), 1)
    actual_total = len(result.requirements)
    fr_count = sum(1 for r in result.requirements if r.req_type == "FR")
    nfr_count = sum(1 for r in result.requirements if r.req_type == "NFR")
    ambiguous_count = sum(1 for r in result.requirements if r.is_ambiguous)
    clean_count = actual_total - ambiguous_count

    fr_pct = int((fr_count / total_reqs) * 100)
    nfr_pct = int((nfr_count / total_reqs) * 100)
    quality_pct = int((clean_count / total_reqs) * 100)
    total_sec = result.timings.get("total_execution_sec", 0.0)

    quality_color = "#16A34A" if quality_pct >= 80 else ("#D97706" if quality_pct >= 50 else "#DC2626")

    cards_html = f"""
<div class="summary-grid">
    <div class="summary-card">
        <div class="summary-top">
            <span class="summary-label">Tổng số Yêu cầu</span>
            <span style="color: #1E40AF;">{svg_icon("layers")}</span>
        </div>
        <div class="summary-number">{actual_total} câu</div>
        <div class="summary-explain">Đã tách tự động từ văn bản của bạn</div>
        <div class="meter-bg">
            <div class="meter-bar" style="width: 100%; background: #1E40AF;"></div>
        </div>
    </div>
    <div class="summary-card">
        <div class="summary-top">
            <span class="summary-label">Tính năng Hệ thống</span>
            <span style="color: #0F766E;">{svg_icon("cpu")}</span>
        </div>
        <div class="summary-number" style="color: #0F766E;">{fr_count} câu</div>
        <div class="summary-explain">Việc phần mềm cần làm cho người dùng ({fr_pct}%)</div>
        <div class="meter-bg">
            <div class="meter-bar" style="width: {fr_pct}%; background: #0F766E;"></div>
        </div>
    </div>
    <div class="summary-card">
        <div class="summary-top">
            <span class="summary-label">Yêu cầu Chất lượng</span>
            <span style="color: #1D4ED8;">{svg_icon("shield")}</span>
        </div>
        <div class="summary-number" style="color: #1D4ED8;">{nfr_count} câu</div>
        <div class="summary-explain">Tiêu chuẩn tốc độ, bảo mật, độ ổn định ({nfr_pct}%)</div>
        <div class="meter-bg">
            <div class="meter-bar" style="width: {nfr_pct}%; background: #1D4ED8;"></div>
        </div>
    </div>
    <div class="summary-card">
        <div class="summary-top">
            <span class="summary-label">Độ rõ ràng của câu</span>
            <span style="color: {quality_color};">{svg_icon("sparkles")}</span>
        </div>
        <div class="summary-number" style="color: {quality_color};">{quality_pct}%</div>
        <div class="summary-explain">{clean_count} câu đã rõ · {ambiguous_count} câu cần viết cụ thể hơn</div>
        <div class="meter-bg">
            <div class="meter-bar" style="width: {quality_pct}%; background: {quality_color};"></div>
        </div>
    </div>
    <div class="summary-card">
        <div class="summary-top">
            <span class="summary-label">Thời gian xử lý</span>
            <span style="color: #475569;">{svg_icon("clock")}</span>
        </div>
        <div class="summary-number">{total_sec:.2f} giây</div>
        <div class="summary-explain">Đã tạo sẵn {len(result.user_stories)} kịch bản &amp; file Word</div>
        <div class="meter-bg">
            <div class="meter-bar" style="width: 100%; background: #475569;"></div>
        </div>
    </div>
</div>
    """
    render_html(cards_html)


def _render_confusion_matrix_html(cm: list) -> str:
    """Kết xuất bảng đối chiếu kết quả dự đoán dễ đọc."""
    if not cm or len(cm) < 2 or len(cm[0]) < 2:
        return ""
    c00, c01 = cm[0][0], cm[0][1]
    c10, c11 = cm[1][0], cm[1][1]
    return (
        '<table class="cm-table">'
        '<thead><tr><th>Thực tế \\ Dự đoán</th><th>Đoán là Tính năng</th><th>Đoán là Chất lượng</th></tr></thead>'
        '<tbody>'
        f'<tr><th>Thực tế là Tính năng</th><td class="cm-good">{c00} câu đúng</td>'
        f'<td class="cm-miss">{c01} câu nhầm</td></tr>'
        f'<tr><th>Thực tế là Chất lượng</th><td class="cm-miss">{c10} câu nhầm</td>'
        f'<td class="cm-good">{c11} câu đúng</td></tr>'
        '</tbody></table>'
    )


def render_workbench(facade: RequirementAnalysisFacade, result: AnalysisResultDTO, config: dict = None):
    """Render Bàn làm việc chính với 4 thẻ chức năng trực quan."""
    config = config or {}
    has_valid_key = config.get("has_valid_key", False)
    provider = config.get("provider", "offline")

    # Thông báo rõ ràng về chế độ đã tạo ra kết quả để người dùng không thắc mắc
    if not has_valid_key and provider != "offline":
        render_html(
            """
<div style="background: #FFFBEB; border: 1px solid #FCD34D; color: #92400E;
            padding: 12px 16px; border-radius: 10px; font-size: 0.88rem; margin-bottom: 14px; line-height: 1.5;">
    <b>Giải thích vì sao bạn chưa nhập API Key mà hệ thống vẫn ra kết quả:</b><br>
    Do ô API Key ở thanh bên trái đang để trống, hệ thống đã <b>tự động dùng Bộ Học máy &amp; Từ điển mẫu
    có sẵn trong máy (Chế độ Offline dự phòng)</b> để bạn vẫn xem và tải thử tài liệu được ngay.
    Nếu muốn AI phân tích sâu và viết câu mượt mà hơn, hãy dán API Key vào thanh bên trái rồi bấm Phân tích lại.
</div>
            """
        )

    # 1. Thanh tiến trình 6 bước đã hoàn tất
    total_sec_val = result.timings.get("total_execution_sec", 0.0)
    pipeline_html = build_pipeline_console_html(
        active_step=6,
        status_title=f"Đã hoàn tất phân tích 6 bước cho dự án: {result.project.project_name}",
        status_detail=f"Tệp nguồn: {result.project.source_filename} · Tổng thời gian: {total_sec_val:.2f} giây",
        timings=result.timings,
        is_running=False,
    )
    render_html(pipeline_html)

    # 2. Dải 5 thẻ tổng quan
    _render_summary_cards(result)

    # 3. Bốn Thẻ Kết quả (4 Tabs)
    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Danh sách Yêu cầu & Sửa câu mơ hồ",
        "2. Kịch bản Người dùng & Kiểm thử",
        "3. Sơ đồ Tổng quan & Tải file Word (SRS)",
        "4. Kiểm tra Độ chính xác Mô hình",
    ])

    # ==========================================================================
    # TAB 1: DANH SÁCH YÊU CẦU & GỢI Ý SỬA CÂU MƠ HỒ
    # ==========================================================================
    with tab1:
        f_col1, f_col2, f_col3 = st.columns([2.2, 2.2, 1.6])
        with f_col1:
            filter_mode = st.selectbox(
                "Lọc xem theo nhóm yêu cầu:",
                [
                    "Xem tất cả các câu yêu cầu",
                    "Chỉ xem Tính năng hệ thống (Chức năng)",
                    "Chỉ xem Yêu cầu Chất lượng / Bảo mật (Phi chức năng)",
                    "Chỉ xem các câu đang viết chung chung (Cần làm rõ)",
                    "Chỉ xem các câu đã viết rõ ràng",
                ],
                key="req_filter_mode",
            )
        with f_col2:
            search_query = st.text_input(
                "Tìm nhanh theo từ khóa:",
                placeholder="Gõ từ khóa cần tìm (ví dụ: thanh toán, đăng nhập...)",
                key="req_search_query",
            )
        with f_col3:
            render_html("<div style='height: 28px;'></div>")
            ambiguous_ids = [r.req_id for r in result.requirements if r.is_ambiguous and r.smart_rewrite]
            if st.button(
                f"Áp dụng gợi ý rõ ràng cho tất cả ({len(ambiguous_ids)} câu)",
                disabled=(len(ambiguous_ids) == 0),
                use_container_width=True,
                type="primary",
                key="btn_apply_all_smart",
            ):
                for r_id in ambiguous_ids:
                    facade.apply_smart_rewrite(r_id)
                st.session_state["analysis_result"] = facade.get_current_result()
                st.rerun()

        filtered_reqs = []
        for req in result.requirements:
            if filter_mode == "Chỉ xem Tính năng hệ thống (Chức năng)" and req.req_type != "FR":
                continue
            if filter_mode == "Chỉ xem Yêu cầu Chất lượng / Bảo mật (Phi chức năng)" and req.req_type != "NFR":
                continue
            if filter_mode == "Chỉ xem các câu đang viết chung chung (Cần làm rõ)" and not req.is_ambiguous:
                continue
            if filter_mode == "Chỉ xem các câu đã viết rõ ràng" and req.is_ambiguous:
                continue
            if search_query.strip():
                q = search_query.strip().lower()
                if q not in req.req_id.lower() and q not in req.raw_text.lower():
                    continue
            filtered_reqs.append(req)

        if not filtered_reqs:
            st.info("Không có câu yêu cầu nào nằm trong nhóm bộ lọc bạn đang chọn.")

        for req in filtered_reqs:
            if req.req_type == "FR":
                type_cls = "badge-fr"
                type_label = "Tính năng hệ thống (Chức năng)"
            else:
                type_cls = "badge-nfr"
                type_label = "Yêu cầu Chất lượng (Phi chức năng)"

            vi_cat = ISO_VI_LABELS.get(req.nfr_category, req.nfr_category or "")
            iso_badge = (
                f'<span class="badge-sub">Nhóm: {html.escape(vi_cat)}</span>'
                if vi_cat
                else ""
            )

            status_badge = (
                '<span class="badge-warn">Cần làm rõ thêm</span>'
                if req.is_ambiguous
                else '<span class="badge-ok">Đã viết rõ ràng</span>'
            )

            conf_pct = int(req.confidence * 100)
            highlighted_html = highlight_vague_terms(req.raw_text, req.vague_terms)

            details_html = ""
            if req.is_ambiguous:
                reasons = []
                if req.vague_terms:
                    escaped_terms = ", ".join(html.escape(t) for t in req.vague_terms)
                    reasons.append(
                        f"Đang dùng từ mang tính cảm tính: <b>{escaped_terms}</b> "
                        "(nên thay bằng con số cụ thể để dễ nghiệm thu)"
                    )
                if req.missing_actor:
                    reasons.append("Chưa ghi rõ ai là người thực hiện hoặc sử dụng tính năng này")
                if req.missing_metric:
                    reasons.append("Yêu cầu chất lượng nhưng chưa có con số đo lường (ví dụ: bao nhiêu giây, bao nhiêu %)")

                details_html += (
                    f'<div class="issue-explain-box">'
                    f'<b>Vì sao câu này cần làm rõ?</b><br>• {"<br>• ".join(reasons)}'
                    f'</div>'
                )

                if req.smart_rewrite and req.smart_rewrite != req.raw_text:
                    details_html += (
                        f'<div class="smart-suggest-box">'
                        f'<b>Gợi ý viết lại rõ ràng &amp; đầy đủ hơn:</b><br>'
                        f'{html.escape(req.smart_rewrite)}'
                        f'</div>'
                    )

            card_html = f"""
<div class="req-card">
    <div class="req-header">
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px;">
            <span class="badge-id">{html.escape(req.req_id)}</span>
            <span class="{type_cls}">{type_label}</span>
            {iso_badge}
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span class="badge-sub">Độ tin cậy: {conf_pct}%</span>
            {status_badge}
        </div>
    </div>
    <div class="req-content">{highlighted_html}</div>
    {details_html}
</div>
            """
            render_html(card_html)

            # Hàng nút thao tác gọn gàng ngay bên dưới thẻ khi cần áp dụng câu gợi ý hoặc đổi phân loại
            act_col1, act_col2 = st.columns([2, 3])
            with act_col1:
                if req.is_ambiguous and req.smart_rewrite and req.smart_rewrite != req.raw_text:
                    if st.button(
                        f"Dùng câu gợi ý này cho {req.req_id}",
                        key=f"btn_smart_{req.req_id}",
                        use_container_width=True,
                        type="primary",
                    ):
                        facade.apply_smart_rewrite(req.req_id)
                        st.session_state["analysis_result"] = facade.get_current_result()
                        st.rerun()

            with act_col2:
                with st.expander(f"Tùy chỉnh lại phân loại của {req.req_id} (nếu muốn sửa thủ công)"):
                    e_c1, e_c2, e_c3 = st.columns([1.5, 2, 1.2])
                    with e_c1:
                        type_options = ["Tính năng (FR)", "Chất lượng (NFR)"]
                        new_type_label = st.selectbox(
                            "Loại yêu cầu",
                            type_options,
                            index=0 if req.req_type == "FR" else 1,
                            key=f"sel_type_{req.req_id}",
                        )
                        new_type = "FR" if "FR" in new_type_label else "NFR"
                    with e_c2:
                        current_cat_idx = (
                            ISO_CATEGORIES.index(req.nfr_category)
                            if req.nfr_category in ISO_CATEGORIES
                            else 0
                        )
                        new_cat = None
                        if new_type == "NFR":
                            cat_display_list = [f"{ISO_VI_LABELS[k]} ({k})" for k in ISO_CATEGORIES]
                            chosen_cat_display = st.selectbox(
                                "Nhóm tiêu chuẩn chất lượng",
                                cat_display_list,
                                index=current_cat_idx,
                                key=f"sel_cat_{req.req_id}",
                            )
                            new_cat = ISO_CATEGORIES[cat_display_list.index(chosen_cat_display)]
                    with e_c3:
                        render_html("<div style='height: 28px;'></div>")
                        if st.button("Lưu thay đổi", key=f"btn_save_type_{req.req_id}", use_container_width=True):
                            facade.update_requirement_type(req.req_id, new_type, new_cat)
                            st.session_state["analysis_result"] = facade.get_current_result()
                            st.rerun()

    # ==========================================================================
    # TAB 2: KỊCH BẢN NGƯỜI DÙNG & TIÊU CHÍ KIỂM THỬ (USER STORIES)
    # ==========================================================================
    with tab2:
        render_html(
            f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
    <div>
        <div style="font-size:1.1rem; font-weight:700; color:#0F172A;">
            Kịch bản Người dùng &amp; Các tình huống Kiểm thử nghiệm thu
        </div>
        <div style="font-size:0.86rem; color:#64748B;">
            Diễn giải từng câu yêu cầu thành góc nhìn của người sử dụng thực tế và cách kiểm tra xem phần mềm đã làm đúng chưa.
        </div>
    </div>
    <span class="badge-sub">Tổng cộng: {len(result.user_stories)} kịch bản</span>
</div>
            """
        )

        for us in result.user_stories:
            ac_blocks_html = []
            for idx_ac, ac in enumerate(us.acceptance_criteria, start=1):
                ac_blocks_html.append(
                    f'<div class="test-scenario-box">'
                    f'<div class="test-scenario-header">Tình huống kiểm thử {idx_ac}: {html.escape(ac.scenario)}</div>'
                    f'<div><span class="tag-given">• Bối cảnh ban đầu:</span> {html.escape(ac.given)}</div>'
                    f'<div><span class="tag-when">• Khi thao tác:</span> {html.escape(ac.when)}</div>'
                    f'<div><span class="tag-then">• Kết quả phải đạt:</span> {html.escape(ac.then)}</div>'
                    f'</div>'
                )

            story_html = f"""
<div class="us-card">
    <div class="req-header">
        <div style="display:flex; flex-wrap:wrap; align-items:center; gap:8px;">
            <span class="badge-id">{html.escape(us.story_id)}</span>
            <span class="badge-fr">Từ yêu cầu gốc: {html.escape(us.req_id)}</span>
            <span class="badge-sub">Tên chức năng: {html.escape(us.puml_usecase_name)}</span>
        </div>
        <span class="badge-ok">{len(us.acceptance_criteria)} tình huống kiểm thử</span>
    </div>
    <div class="us-grid">
        <div class="us-box">
            <div class="us-box-title">1. Ai là người sử dụng?</div>
            <div class="us-box-value">Là một <b>{html.escape(us.role)}</b></div>
        </div>
        <div class="us-box">
            <div class="us-box-title">2. Họ muốn làm việc gì?</div>
            <div class="us-box-value">Tôi muốn <b>{html.escape(us.goal)}</b></div>
        </div>
        <div class="us-box">
            <div class="us-box-title">3. Để mang lại lợi ích gì?</div>
            <div class="us-box-value">Để <b>{html.escape(us.benefit)}</b></div>
        </div>
    </div>
    {"".join(ac_blocks_html)}
</div>
            """
            render_html(story_html)

        # KHU VỰC XUẤT & ĐỒNG BỘ SANG JIRA / GITHUB / TRELLO
        render_html(
            f"""
<div style="margin-top: 28px; margin-bottom: 14px; padding-top: 18px; border-top: 1px solid #E2E8F0;">
    <div style="display:flex; align-items:center; gap:10px;">
        <span style="color:#1E40AF;">{svg_icon("share")}</span>
        <div>
            <div style="font-size:1.1rem; font-weight:700; color:#0F172A;">
                Xuất danh sách công việc sang Phần mềm Quản lý Dự án (Jira / GitHub / Trello)
            </div>
            <div style="font-size:0.86rem; color:#64748B;">
                Bạn có thể bấm tải file về máy ngay lập tức (không cần tài khoản) hoặc nhập mã kết nối để đẩy thẳng lên dự án.
            </div>
        </div>
    </div>
</div>
            """
        )

        col_jira, col_gh, col_trello = st.columns(3)

        with col_jira:
            render_html(
                """
<div class="req-card" style="margin-bottom: 8px;">
    <div class="req-header" style="margin-bottom: 6px; padding-bottom: 6px;">
        <span class="badge-id" style="background:#1D4ED8;">1. Atlassian Jira</span>
        <span class="badge-sub">File CSV &amp; Cloud</span>
    </div>
    <div style="font-size:0.83rem; color:#475569;">
        Tải file bảng tính CSV để nhập vào Jira hoặc đẩy trực tiếp lên Jira Cloud.
    </div>
</div>
                """
            )
            jira_csv = facade.export_jira_csv()
            st.download_button(
                "Tải file Jira (.csv) về máy ngay",
                data=jira_csv,
                file_name=f"{result.project.project_name}_jira_stories.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_jira_csv",
            )
            with st.expander("Hoặc đẩy trực tiếp lên Jira qua tài khoản API"):
                j_domain = st.text_input("Địa chỉ Jira Domain", placeholder="ten-cong-ty.atlassian.net")
                j_email = st.text_input("Email đăng nhập Jira", placeholder="email@company.com")
                j_token = st.text_input("Mã Jira API Token", type="password")
                j_key = st.text_input("Mã Dự án (Project Key)", value="PROJ", max_chars=10)
                if st.button("Đẩy lên Jira Cloud", key="btn_sync_jira", use_container_width=True):
                    if not (j_domain and j_email and j_token and j_key):
                        st.warning("Vui lòng điền đủ 4 thông tin kết nối Jira phía trên.")
                    else:
                        with st.spinner("Đang gửi danh sách công việc lên Jira..."):
                            res = facade.sync_to_jira(j_domain, j_email, j_token, j_key)
                            if res["success_count"] > 0:
                                st.success(f"Đã tạo thành công {res['success_count']} đầu việc trên Jira!")
                            if res["errors"]:
                                err_msg = res["errors"][0].get("error", "Lỗi không xác định")
                                st.error(f"Gặp {len(res['errors'])} lỗi: {err_msg}")

        with col_gh:
            render_html(
                """
<div class="req-card" style="margin-bottom: 8px;">
    <div class="req-header" style="margin-bottom: 6px; padding-bottom: 6px;">
        <span class="badge-id" style="background:#0F172A;">2. GitHub Issues</span>
        <span class="badge-sub">File JSON &amp; API</span>
    </div>
    <div style="font-size:0.83rem; color:#475569;">
        Tải file dữ liệu JSON hoặc tự động tạo danh sách Issues trên kho mã nguồn GitHub.
    </div>
</div>
                """
            )
            gh_json = facade.export_github_json()
            st.download_button(
                "Tải file GitHub Issues (.json) về máy",
                data=gh_json,
                file_name=f"{result.project.project_name}_github_issues.json",
                mime="application/json",
                use_container_width=True,
                key="dl_gh_json",
            )
            with st.expander("Hoặc đẩy trực tiếp lên kho GitHub"):
                gh_repo = st.text_input("Tên kho GitHub (owner/repo)", placeholder="username/ten-du-an")
                gh_token = st.text_input("Mã GitHub Token (PAT)", type="password")
                if st.button("Đẩy lên GitHub Issues", key="btn_sync_github", use_container_width=True):
                    if not (gh_repo and gh_token):
                        st.warning("Vui lòng nhập tên kho GitHub và mã Token.")
                    else:
                        with st.spinner("Đang tạo Issues trên GitHub..."):
                            res = facade.sync_to_github(gh_repo, gh_token)
                            if res["success_count"] > 0:
                                st.success(f"Đã tạo thành công {res['success_count']} Issues trên GitHub!")
                            if res["errors"]:
                                err_msg = res["errors"][0].get("error", "Lỗi kết nối")
                                st.error(f"Gặp {len(res['errors'])} lỗi: {err_msg}")

        with col_trello:
            render_html(
                """
<div class="req-card" style="margin-bottom: 8px;">
    <div class="req-header" style="margin-bottom: 6px; padding-bottom: 6px;">
        <span class="badge-id" style="background:#0F766E;">3. Bảng Trello</span>
        <span class="badge-sub">File JSON &amp; Card</span>
    </div>
    <div style="font-size:0.83rem; color:#475569;">
        Tải file cấu trúc bảng Trello hoặc tạo thẻ công việc trực tiếp lên bảng Trello.
    </div>
</div>
                """
            )
            trello_json = facade.export_trello_json()
            st.download_button(
                "Tải file Trello Board (.json) về máy",
                data=trello_json,
                file_name=f"{result.project.project_name}_trello_board.json",
                mime="application/json",
                use_container_width=True,
                key="dl_trello_json",
            )
            with st.expander("Hoặc tạo thẻ trực tiếp trên bảng Trello"):
                t_key = st.text_input("Trello API Key")
                t_token = st.text_input("Trello Token", type="password")
                t_list = st.text_input("Mã cột Trello (List ID)")
                if st.button("Đẩy lên Trello Board", key="btn_sync_trello", use_container_width=True):
                    if not (t_key and t_token and t_list):
                        st.warning("Vui lòng điền đủ Trello API Key, Token và List ID.")
                    else:
                        with st.spinner("Đang tạo thẻ trên Trello..."):
                            res = facade.sync_to_trello(t_key, t_token, t_list)
                            if res["success_count"] > 0:
                                st.success(f"Đã tạo thành công {res['success_count']} thẻ trên Trello!")
                            if res["errors"]:
                                err_msg = res["errors"][0].get("error", "Lỗi kết nối")
                                st.error(f"Gặp {len(res['errors'])} lỗi: {err_msg}")

    # ==========================================================================
    # TAB 3: SƠ ĐỒ TỔNG QUAN & TẢI TÀI LIỆU WORD (SRS)
    # ==========================================================================
    with tab3:
        col_left, col_right = st.columns([1.05, 1.15])

        with col_left:
            render_html(
                f"""
<div class="req-card">
    <div class="req-header">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="color:#1E40AF;">{svg_icon("git-branch")}</span>
            <span style="font-weight:700; font-size:1rem;">Sơ đồ Chức năng Tổng quan (Use Case Diagram)</span>
        </div>
        <span class="badge-sub">Hình vẽ tự động</span>
    </div>
    <div style="font-size:0.85rem; color:#475569;">
        Sơ đồ minh họa trực quan những nhóm người dùng nào sẽ tương tác với các tính năng nào trong hệ thống.
    </div>
</div>
                """
            )

            dl_u1, dl_u2 = st.columns(2)
            with dl_u1:
                if result.plantuml_image_bytes:
                    st.download_button(
                        "Tải hình ảnh Sơ đồ (.png)",
                        data=result.plantuml_image_bytes,
                        file_name=f"{result.project.project_name}_usecase.png",
                        mime="image/png",
                        use_container_width=True,
                        type="primary",
                    )
            with dl_u2:
                st.download_button(
                    "Tải mã vẽ sơ đồ (.puml)",
                    data=result.plantuml_code,
                    file_name=f"{result.project.project_name}_usecase.puml",
                    mime="text/plain",
                    use_container_width=True,
                )

            if result.plantuml_image_bytes:
                st.image(
                    result.plantuml_image_bytes,
                    caption=f"Sơ đồ tổng quan các chức năng của dự án {result.project.project_name}",
                    use_container_width=True,
                )
            else:
                st.info("Hiện máy đang ngoại tuyến nên chưa tải được ảnh sơ đồ. Bạn có thể xem mã sơ đồ bên dưới:")

            with st.expander("Xem mã vẽ sơ đồ kỹ thuật (PlantUML)", expanded=False):
                st.code(result.plantuml_code, language="plantuml")

        with col_right:
            render_html(
                f"""
<div class="req-card">
    <div class="req-header">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="color:#0F766E;">{svg_icon("file-text")}</span>
            <span style="font-weight:700; font-size:1rem;">Tài liệu Đặc tả Phần mềm Hoàn chỉnh (Báo cáo SRS)</span>
        </div>
        <span class="badge-ok">Sẵn sàng tải về</span>
    </div>
    <div style="font-size:0.85rem; color:#475569;">
        Tài liệu đã được trình bày sẵn thành 6 chương mục bài bản (Giới thiệu, Người dùng, Tính năng,
        Tiêu chuẩn chất lượng, Kịch bản &amp; Bảng đối chiếu). Bạn có thể tải file Word về sử dụng ngay.
    </div>
</div>
                """
            )

            docx_bytes = facade.export_srs_docx()
            md_text = facade.export_srs_markdown()

            dl_s1, dl_s2 = st.columns(2)
            with dl_s1:
                st.download_button(
                    "Tải về file Microsoft Word (.docx)",
                    data=docx_bytes,
                    file_name=f"{result.project.project_name}_Tai_lieu_SRS.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    type="primary",
                )
            with dl_s2:
                st.download_button(
                    "Tải về file Văn bản Markdown (.md)",
                    data=md_text,
                    file_name=f"{result.project.project_name}_Tai_lieu_SRS.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            with st.container(height=520, border=True):
                st.markdown(md_text)

    # ==========================================================================
    # TAB 4: KIỂM TRA ĐỘ CHÍNH XÁC CỦA MÔ HÌNH PHÂN LOẠI
    # ==========================================================================
    with tab4:
        top_b1, top_b2 = st.columns([3.5, 1.2])
        with top_b1:
            render_html(
                f"""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
    <span style="color:#1E40AF;">{svg_icon("bar-chart")}</span>
    <div>
        <div style="font-size:1.1rem; font-weight:700; color:#0F172A;">
            Đo lường Độ chính xác của thuật toán trên 35 câu đề bài mẫu
        </div>
        <div style="font-size:0.85rem; color:#64748B;">
            So sánh tỷ lệ đoán đúng giữa 3 phương pháp: Dò từ khóa đơn giản, Học máy nội bộ (LinearSVC) và Kết hợp AI.
        </div>
    </div>
</div>
                """
            )
        with top_b2:
            rerun_bench = st.button(
                "Chạy đo lường lại",
                key="btn_run_benchmark",
                use_container_width=True,
            )

        if "benchmark_cache" not in st.session_state or rerun_bench:
            evaluator = BenchmarkEvaluator()
            kw_metrics = evaluator.evaluate_keyword_baseline()
            ml_metrics = evaluator.evaluate_offline_ml_kfold(n_splits=5)
            hybrid_metrics = evaluator.evaluate_hybrid_classifier(facade.classifier)
            st.session_state["benchmark_cache"] = (kw_metrics, ml_metrics, hybrid_metrics)

        kw_metrics, ml_metrics, hybrid_metrics = st.session_state["benchmark_cache"]

        tiers = [
            ("Phương pháp 1: Dò từ khóa", "Chỉ tìm từ khóa cố định trong câu", kw_metrics, "#475569"),
            ("Phương pháp 2: Học máy có sẵn", "Mô hình TF-IDF + LinearSVC (Kiểm tra chéo 5 lần)", ml_metrics, "#0F766E"),
            ("Phương pháp 3: Hệ thống Lai ghép", "Kết hợp Học máy nội bộ và Mô hình AI", hybrid_metrics, "#1E40AF"),
        ]

        b_cols = st.columns(3)
        for col, (tier_title, tier_desc, m_data, accent_hex) in zip(b_cols, tiers):
            acc_pct = m_data["accuracy"] * 100
            macro_f1 = m_data["macro_f1"]
            fr_f1 = m_data["fr_f1"]
            nfr_f1 = m_data["nfr_f1"]
            cm_html = _render_confusion_matrix_html(m_data["confusion_matrix"])

            with col:
                bench_card_html = f"""
<div class="req-card">
    <div class="req-header">
        <span class="badge-id" style="background:{accent_hex};">{tier_title}</span>
        <span class="badge-ok">{m_data['total_samples']} câu mẫu</span>
    </div>
    <div style="font-size:0.83rem; color:#64748B; margin-bottom:12px;">{tier_desc}</div>
    <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px;">
        <span class="summary-label">Tỷ lệ phân loại đúng (Accuracy)</span>
        <span class="summary-number" style="font-size:1.5rem; color:{accent_hex};">{acc_pct:.1f}%</span>
    </div>
    <div class="meter-bg" style="margin-bottom:12px;">
        <div class="meter-bar" style="width:{acc_pct}%; background:{accent_hex};"></div>
    </div>
    <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; margin-bottom:12px;
                font-size:0.8rem; text-align:center;">
        <div style="background:#F8FAFC; padding:6px; border-radius:6px; border:1px solid #E2E8F0;">
            <div style="color:#64748B; font-size:0.73rem;">Điểm F1 Chung</div>
            <div style="font-weight:700; color:#0F172A;">{macro_f1:.3f}</div>
        </div>
        <div style="background:#F8FAFC; padding:6px; border-radius:6px; border:1px solid #E2E8F0;">
            <div style="color:#64748B; font-size:0.73rem;">Điểm Tính năng</div>
            <div style="font-weight:700; color:#0F766E;">{fr_f1:.3f}</div>
        </div>
        <div style="background:#F8FAFC; padding:6px; border-radius:6px; border:1px solid #E2E8F0;">
            <div style="color:#64748B; font-size:0.73rem;">Điểm Chất lượng</div>
            <div style="font-weight:700; color:#1D4ED8;">{nfr_f1:.3f}</div>
        </div>
    </div>
    <div style="font-size:0.78rem; font-weight:600; color:#475569;">
        Bảng chi tiết số câu đoán đúng / đoán nhầm:
    </div>
    {cm_html}
</div>
                """
                render_html(bench_card_html)
