# BA-Gen (ReqAssist-NLP)

**Hệ thống Trợ lý Phân tích Yêu cầu Phần mềm sử dụng Xử lý Ngôn ngữ Tự nhiên (NLP) và Mô hình Ngôn ngữ Lớn (LLM) đa nhà cung cấp.**

> **Trạng thái hiện tại:** Khung dự án ban đầu (*Project Skeleton*). Các tính năng nghiệp vụ và bài kiểm thử sẽ được triển khai lần lượt theo 17 Issues trên GitHub.

---

## Giới thiệu nhanh

**BA-Gen (ReqAssist-NLP)** hỗ trợ Chuyên viên Phân tích Nghiệp vụ (Business Analyst — BA) và Kỹ sư Yêu cầu tự động hóa chuỗi công việc từ tài liệu mô tả bài toán thô (`.txt`, `.docx` hoặc văn bản thuần bằng **Tiếng Việt** và **Tiếng Anh**) sang bộ đặc tả phần mềm chuẩn hóa:

1. **Đọc tài liệu & Tách câu nguyên tử:** Hỗ trợ `.txt`, `.docx` (gồm bảng biểu) và văn bản dán trực tiếp, chuẩn hóa Unicode `NFC`.
2. **Phân loại FR / NFR lai ghép:** Kết hợp mô hình học máy thống kê cục bộ (`TF-IDF + LinearSVC`) với cổng LLM đa nhà cung cấp (**Groq**, **OpenRouter**, **Gemini**, tùy chọn **Ollama**) qua chuẩn `OpenAI-compatible API`, kèm cơ chế dự phòng ngoại tuyến tự động (*Offline ML Fallback*).
3. **Phát hiện mơ hồ & Gợi ý chuẩn SMART:** Tô sáng từ ngữ định tính cảm tính, cảnh báo thiếu tác nhân (*Missing Actor*), thiếu chỉ số định lượng (*Missing Metric*) và đề xuất viết lại câu theo chuẩn SMART.
4. **Sinh Agile User Stories & Tiêu chí Nghiệm thu Gherkin:** Tự động bóc tách `Role - Goal - Benefit` kèm tối thiểu 2 kịch bản `GIVEN / WHEN / THEN`.
5. **Xuất tài liệu SRS rút gọn & Sơ đồ Use Case:** Đóng gói tệp Word (`.docx`) / Markdown (`.md`) theo chuẩn IEEE 830 / ISO 29148 và kết xuất sơ đồ Use Case PlantUML qua **Kroki API**.
6. **Kiểm chuẩn mô hình (Benchmark):** Đánh giá độ chính xác phân loại trên bộ 35 câu yêu cầu song ngữ gán nhãn thủ công.

---

## Cấu trúc thư mục khung hiện tại

```text
BA-Gen/
├── .github/
│   └── workflows/          # Quy trình CI/CD GitHub Actions (triển khai ở Issue #17)
├── data/                   # Dữ liệu kiểm chuẩn 35 câu & từ điển mơ hồ (Issue #3)
├── docs/
│   ├── ARCHITECTURE_AND_SPEC.md   # Tài liệu Kiến trúc, Công nghệ & Đặc tả Hệ thống
│   └── IMPLEMENTATION_PLAN.md     # Kế hoạch 4 Sprints, 17 Issues & Kiểm thử
├── src/
│   ├── core/               # Lược đồ Pydantic, SQLite Cache & RequirementAnalysisFacade
│   ├── parsers/            # Đọc tệp đa định dạng (Factory) & tách câu song ngữ
│   ├── classifiers/        # Baseline, Offline LinearSVC, Multi-LLM & Benchmark
│   ├── analyzers/          # Phát hiện từ mơ hồ, thiếu Actor/Metric & gợi ý SMART
│   ├── generators/         # Sinh Agile User Stories & Gherkin Acceptance Criteria
│   ├── exporters/          # Xuất SRS rút gọn (.docx/.md) & PlantUML (Kroki API)
│   ├── ui/                 # Thành phần giao diện Streamlit
│   └── utils/              # Quản lý từ điển Singleton & tiện ích dùng chung
├── tests/                  # Bộ kiểm thử đơn vị và kiểm thử tích hợp (Issue #16)
├── .gitignore
└── README.md
```

---

## Tài liệu & Theo dõi Tiến độ

- **Tài liệu Kiến trúc & Đặc tả Hệ thống:** [docs/ARCHITECTURE_AND_SPEC.md](docs/ARCHITECTURE_AND_SPEC.md)
- **Kế hoạch Triển khai & Lộ trình 4 Sprints:** [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- **Danh sách 17 Issues & 4 Milestones:** https://github.com/nguyentrananhhoang13122005/BA-Gen/issues
