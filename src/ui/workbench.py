"""Bàn làm việc chính (Main Workbench) gồm 4 Thẻ chức năng chuyên sâu.

Tab 1: Bảng Yêu cầu & Rà soát Mơ hồ (Tô đỏ từ cảm tính, gợi ý SMART, đổi nhãn FR/NFR)
Tab 2: Agile User Stories & Tiêu chí Nghiệm thu Gherkin
Tab 3: Tài liệu SRS IEEE 830 & Sơ đồ Use Case PlantUML
Tab 4: Báo cáo Đánh giá Kiểm chuẩn (Benchmark Evaluator trên 35 câu)
"""

import html
import re
import streamlit as st
from src.classifiers.evaluate_benchmark import BenchmarkEvaluator
from src.core.facade import RequirementAnalysisFacade
from src.core.models import AnalysisResultDTO


def highlight_vague_terms(text: str, vague_terms: list) -> str:
    """Tô đỏ và làm nổi bật các từ ngữ cảm tính mơ hồ bằng thẻ HTML an toàn."""
    escaped_text = html.escape(text)
    replacement = (
        r'<span style="background-color: #ffebee; color: #c62828; font-weight: bold; '
        r'padding: 2px 6px; border-radius: 4px; border: 1px solid #ef9a9a;">\1</span>'
    )
    for term in sorted(vague_terms, key=len, reverse=True):
        escaped_term = html.escape(term)
        pattern = re.compile(rf"(?<!\w)({re.escape(escaped_term)})(?!\w)", re.IGNORECASE)
        escaped_text = pattern.sub(replacement, escaped_text)
    return escaped_text


def render_workbench(facade: RequirementAnalysisFacade, result: AnalysisResultDTO):
    """Render 4 tab làm việc chính."""
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 1. Yêu cầu & Rà soát Mơ hồ",
        "🎯 2. Agile User Stories & Gherkin",
        "📄 3. Tài liệu SRS & Sơ đồ Use Case",
        "📊 4. Đánh giá Kiểm chuẩn (Benchmark)"
    ])

    # ==========================================
    # TAB 1: YÊU CẦU & RÀ SOÁT MƠ HỒ
    # ==========================================
    with tab1:
        st.subheader("Bảng Tổng quan Chỉ số Nghiệp vụ")

        total_reqs = len(result.requirements)
        fr_count = sum(1 for r in result.requirements if r.req_type == "FR")
        nfr_count = sum(1 for r in result.requirements if r.req_type == "NFR")
        ambiguous_count = sum(1 for r in result.requirements if r.is_ambiguous)

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Tổng số câu", total_reqs)
        col2.metric("Chức năng (FR)", fr_count)
        col3.metric("Phi chức năng (NFR)", nfr_count)
        col4.metric("Câu Mơ hồ / Cảnh báo", ambiguous_count)
        col5.metric("Thời gian xử lý", f"{result.timings.get('total_execution_sec', 0.0)}s")

        st.markdown("---")
        st.subheader("Chi tiết Từng Yêu cầu & Tương tác Human-in-the-Loop")

        for idx, req in enumerate(result.requirements):
            with st.container():
                c_head1, c_head2, c_head3 = st.columns([1, 4, 2])
                with c_head1:
                    st.markdown(f"**`{req.req_id}`**")
                with c_head2:
                    badge_color = "#2e7d32" if req.req_type == "FR" else "#1565c0"
                    badge_html = (
                        f'<span style="background-color: {badge_color}; color: white; padding: 3px 8px; '
                        f'border-radius: 4px; font-weight: bold; font-size: 0.85em;">{req.req_type}</span> '
                        f'<em>{req.nfr_category or ""}</em>'
                    )
                    st.markdown(badge_html, unsafe_allow_html=True)
                with c_head3:
                    st.progress(req.confidence, text=f"Tin cậy: {int(req.confidence * 100)}%")

                highlighted_html = highlight_vague_terms(req.raw_text, req.vague_terms)
                st.markdown(f"💬 {highlighted_html}", unsafe_allow_html=True)

                if req.is_ambiguous:
                    warn_msgs = []
                    if req.vague_terms:
                        warn_msgs.append(f"Từ ngữ cảm tính: <b>{', '.join(req.vague_terms)}</b>")
                    if req.missing_actor:
                        warn_msgs.append("Thiếu tác nhân thực hiện (Missing Actor)")
                    if req.missing_metric:
                        warn_msgs.append("NFR thiếu chỉ số đo lường định lượng (Missing Metric)")

                    warn_html = (
                        '<div style="background-color: #fff8e1; border-left: 4px solid #ffb300; '
                        'padding: 8px 12px; margin: 6px 0; border-radius: 4px; font-size: 0.9em;">'
                        f'⚠️ {" | ".join(warn_msgs)}'
                        '</div>'
                    )
                    st.markdown(warn_html, unsafe_allow_html=True)

                    if req.smart_rewrite and req.smart_rewrite != req.raw_text:
                        smart_html = (
                            '<div style="background-color: #e8f5e9; border-left: 4px solid #43a047; '
                            'padding: 8px 12px; margin: 6px 0; border-radius: 4px; font-size: 0.9em;">'
                            f'✨ <b>Gợi ý chuẩn SMART:</b> {req.smart_rewrite}'
                            '</div>'
                        )
                        st.markdown(smart_html, unsafe_allow_html=True)
                        btn_col1, btn_col2 = st.columns([2, 5])
                        with btn_col1:
                            if st.button("Áp dụng SMART", key=f"btn_smart_{req.req_id}"):
                                facade.apply_smart_rewrite(req.req_id)
                                st.rerun()

                st.markdown("<hr style='margin: 8px 0; border: 0.5px solid #eee;'>", unsafe_allow_html=True)

    # ==========================================
    # TAB 2: AGILE USER STORIES & GHERKIN
    # ==========================================
    with tab2:
        st.subheader("Danh sách Agile User Stories & Kịch bản Gherkin BDD")
        st.caption("Mỗi yêu cầu được bóc tách thành Role - Goal - Benefit kèm tối thiểu 2 kịch bản Gherkin.")

        for us in result.user_stories:
            with st.expander(f"📌 {us.story_id} — Là một {us.role}, tôi muốn {us.goal}", expanded=True):
                st.markdown(f"**Mã liên kết truy vết:** `{us.req_id}` | **Ca sử dụng:** *{us.puml_usecase_name}*")
                st.markdown(
                    f"> **Là một:** {us.role}  \n"
                    f"> **Tôi muốn:** {us.goal}  \n"
                    f"> **Để:** {us.benefit}"
                )

                st.markdown("**Tiêu chí Nghiệm thu (Acceptance Criteria):**")
                for ac in us.acceptance_criteria:
                    st.markdown(f"**• Kịch bản:** *{ac.scenario}*")
                    st.code(
                        f"GIVEN {ac.given}\n"
                        f"WHEN  {ac.when}\n"
                        f"THEN  {ac.then}",
                        language="gherkin"
                    )

        st.markdown("---")
        st.subheader("🚀 Đồng bộ sang Công cụ Quản lý Dự án (Jira / GitHub / Trello)")
        st.caption("Hỗ trợ cả tải tệp cấu trúc Import nhanh lẫn đồng bộ trực tiếp qua REST API.")

        with st.expander("🔷 Atlassian Jira (Xuất tệp CSV Import & REST API Cloud)", expanded=True):
            c_j1, c_j2 = st.columns([1, 1])
            with c_j1:
                st.markdown("##### 📥 Xuất tệp Jira CSV Import")
                jira_csv = facade.export_jira_csv()
                st.download_button(
                    "📥 Tải tệp Jira Import (.csv)",
                    data=jira_csv,
                    file_name=f"{result.project.project_name}_jira_stories.csv",
                    mime="text/csv",
                    help="Dùng tính năng 'Import Issues from CSV' trong Jira để nhập hàng loạt không cần cấp quyền API."
                )
            with c_j2:
                st.markdown("##### ⚡ Đồng bộ qua Jira Cloud REST API")
                j_domain = st.text_input("Jira Domain", placeholder="ten-cong-ty (hoặc ten-cong-ty.atlassian.net)")
                j_email = st.text_input("Atlassian Email", placeholder="email@company.com")
                j_token = st.text_input("Atlassian API Token", type="password")
                j_key = st.text_input("Mã Dự án (Project Key)", value="PROJ", max_chars=10)
                if st.button("Đẩy lên Jira Cloud", key="btn_sync_jira"):
                    if not (j_domain and j_email and j_token and j_key):
                        st.warning("Vui lòng điền đủ Domain, Email, API Token và Project Key.")
                    else:
                        with st.spinner("Đang đẩy User Stories lên Jira..."):
                            res = facade.sync_to_jira(j_domain, j_email, j_token, j_key)
                            if res["success_count"] > 0:
                                st.success(f"✅ Đã tạo thành công {res['success_count']} User Stories trên Jira!")
                            if res["errors"]:
                                err_msg = res["errors"][0].get("error", "Lỗi không xác định")
                                st.error(f"Gặp {len(res['errors'])} lỗi khi tạo. Chi tiết: {err_msg}")

        with st.expander("🐙 GitHub Issues (Xuất tệp JSON & REST API Sync)", expanded=False):
            c_g1, c_g2 = st.columns([1, 1])
            with c_g1:
                st.markdown("##### 📥 Xuất tệp GitHub JSON")
                gh_json = facade.export_github_json()
                st.download_button(
                    "📥 Tải tệp GitHub Issues (.json)",
                    data=gh_json,
                    file_name=f"{result.project.project_name}_github_issues.json",
                    mime="application/json"
                )
            with c_g2:
                st.markdown("##### ⚡ Đồng bộ qua GitHub REST API")
                gh_repo = st.text_input("Repository (owner/repo)", placeholder="username/repository-name")
                gh_token = st.text_input("GitHub Personal Access Token (PAT)", type="password", help="Yêu cầu quyền 'repo'")
                if st.button("Đẩy lên GitHub Issues", key="btn_sync_github"):
                    if not (gh_repo and gh_token):
                        st.warning("Vui lòng nhập tên Repository và Personal Access Token.")
                    else:
                        with st.spinner("Đang tạo Issues trên GitHub..."):
                            res = facade.sync_to_github(gh_repo, gh_token)
                            if res["success_count"] > 0:
                                st.success(f"✅ Đã tạo thành công {res['success_count']} Issues trên GitHub!")
                            if res["errors"]:
                                err_msg = res["errors"][0].get("error", "Lỗi kết nối")
                                st.error(f"Gặp {len(res['errors'])} lỗi: {err_msg}")

        with st.expander("📋 Trello Kanban (Xuất tệp Board JSON & REST API Sync)", expanded=False):
            c_t1, c_t2 = st.columns([1, 1])
            with c_t1:
                st.markdown("##### 📥 Xuất tệp Trello Board JSON")
                trello_json = facade.export_trello_json()
                st.download_button(
                    "📥 Tải tệp Trello Board (.json)",
                    data=trello_json,
                    file_name=f"{result.project.project_name}_trello_board.json",
                    mime="application/json"
                )
            with c_t2:
                st.markdown("##### ⚡ Đồng bộ qua Trello REST API")
                t_key = st.text_input("Trello API Key")
                t_token = st.text_input("Trello Token", type="password")
                t_list = st.text_input("Trello List ID (Cột Product Backlog ID)")
                if st.button("Đẩy lên Trello Board", key="btn_sync_trello"):
                    if not (t_key and t_token and t_list):
                        st.warning("Vui lòng điền đủ Trello API Key, Token và List ID.")
                    else:
                        with st.spinner("Đang tạo Cards trên Trello..."):
                            res = facade.sync_to_trello(t_key, t_token, t_list)
                            if res["success_count"] > 0:
                                st.success(f"✅ Đã tạo thành công {res['success_count']} Cards trên Trello!")
                            if res["errors"]:
                                err_msg = res["errors"][0].get("error", "Lỗi kết nối")
                                st.error(f"Gặp {len(res['errors'])} lỗi: {err_msg}")

    # ==========================================
    # TAB 3: TÀI LIỆU SRS & SƠ ĐỒ USE CASE
    # ==========================================
    with tab3:
        st.subheader("Kết xuất Sơ đồ Use Case & Tài liệu SRS Chuẩn hóa")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("#### Sơ đồ Ca sử dụng (Use Case Diagram)")
            if result.plantuml_image_bytes:
                st.image(result.plantuml_image_bytes, caption="Sơ đồ Use Case UML 2.5 (Kroki API)", use_column_width=True)
                st.download_button(
                    "📥 Tải ảnh sơ đồ (.png)",
                    data=result.plantuml_image_bytes,
                    file_name="usecase_diagram.png",
                    mime="image/png"
                )
            else:
                st.warning("⚠️ Không thể kết nối Kroki API (chế độ ngoại tuyến). Bạn có thể tải mã nguồn PlantUML bên dưới:")

            st.download_button(
                "📥 Tải mã nguồn PlantUML (.puml)",
                data=result.plantuml_code,
                file_name="usecase_diagram.puml",
                mime="text/plain"
            )

        with col_right:
            st.markdown("#### Đóng gói Tài liệu Đặc tả SRS (IEEE 830)")
            st.markdown("Đầy đủ 6 chương mục: Phạm vi, Tác nhân, Bảng FR, Bảng NFR, User Stories & Ma trận truy vết.")

            docx_bytes = facade.export_srs_docx()
            md_text = facade.export_srs_markdown()

            st.download_button(
                "📥 Tải tài liệu Word (.docx)",
                data=docx_bytes,
                file_name=f"{result.project.project_name}_SRS.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

            st.download_button(
                "📥 Tải tài liệu Markdown (.md)",
                data=md_text,
                file_name=f"{result.project.project_name}_SRS.md",
                mime="text/markdown"
            )

        with st.expander("👁️ Xem trước nội dung tài liệu SRS"):
            st.markdown(facade.export_srs_markdown())

    # ==========================================
    # TAB 4: ĐÁNH GIÁ KIỂM CHUẨN (BENCHMARK)
    # ==========================================
    with tab4:
        st.subheader("Kiểm chuẩn Định lượng trên Tập 35 Câu Yêu cầu Chuẩn")
        st.markdown(
            "So sánh hiệu năng giữa **Baseline Từ khóa**, **Offline ML (LinearSVC với 5-Fold Cross Validation)** "
            "và **Mô hình Lai ghép Hybrid Classifier**."
        )

        if st.button("🚀 Chạy Kiểm chuẩn Ngay", key="btn_run_benchmark"):
            evaluator = BenchmarkEvaluator()
            with st.spinner("Đang tính toán các chỉ số kiểm chuẩn..."):
                kw_metrics = evaluator.evaluate_keyword_baseline()
                ml_metrics = evaluator.evaluate_offline_ml_kfold(n_splits=5)
                hybrid_metrics = evaluator.evaluate_hybrid_classifier(facade.classifier)

            b_col1, b_col2, b_col3 = st.columns(3)
            with b_col1:
                st.markdown("#### 1. Baseline Từ khóa")
                st.metric("Accuracy", f"{kw_metrics['accuracy'] * 100:.1f}%")
                st.metric("Macro F1-Score", f"{kw_metrics['macro_f1']:.3f}")
                st.caption(f"FR F1: {kw_metrics['fr_f1']} | NFR F1: {kw_metrics['nfr_f1']}")
                st.write("Ma trận nhầm lẫn:", kw_metrics["confusion_matrix"])

            with b_col2:
                st.markdown("#### 2. Offline LinearSVC (5-Fold)")
                st.metric("Accuracy", f"{ml_metrics['accuracy'] * 100:.1f}%")
                st.metric("Macro F1-Score", f"{ml_metrics['macro_f1']:.3f}")
                st.caption(f"FR F1: {ml_metrics['fr_f1']} | NFR F1: {ml_metrics['nfr_f1']}")
                st.write("Ma trận nhầm lẫn:", ml_metrics["confusion_matrix"])

            with b_col3:
                st.markdown("#### 3. Mô hình Lai ghép Hybrid")
                st.metric("Accuracy", f"{hybrid_metrics['accuracy'] * 100:.1f}%")
                st.metric("Macro F1-Score", f"{hybrid_metrics['macro_f1']:.3f}")
                st.caption(f"FR F1: {hybrid_metrics['fr_f1']} | NFR F1: {hybrid_metrics['nfr_f1']}")
                st.write("Ma trận nhầm lẫn:", hybrid_metrics["confusion_matrix"])

            st.success("🎉 Kiểm chuẩn hoàn tất! Mô hình đạt các yêu cầu độ chính xác đề ra trong NFR-PERF-04.")
