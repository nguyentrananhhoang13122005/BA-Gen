# BA-Gen (ReqAssist-NLP)

**Hệ thống Trợ lý Phân tích Yêu cầu Phần mềm sử dụng Xử lý Ngôn ngữ Tự nhiên (NLP) và Mô hình Ngôn ngữ Lớn (LLM) đa nhà cung cấp.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/architecture-3--Tier%20Modular%20Monolith-orange.svg)](docs/ARCHITECTURE_AND_SPEC.md)
[![Design Patterns](https://img.shields.io/badge/patterns-5%20GoF-green.svg)](docs/ARCHITECTURE_AND_SPEC.md)
[![Standard](https://img.shields.io/badge/standard-IEEE%20830%20%7C%20ISO%2029148-purple.svg)](docs/ARCHITECTURE_AND_SPEC.md)

> **Trạng thái hiện tại:** Khung dự án ban đầu (*Project Skeleton*). Toàn bộ kiến trúc và lộ trình 4 Sprints / 17 GitHub Issues đã hoàn thiện và sẵn sàng để triển khai mã nguồn.

---

## 📌 Giới thiệu Bài toán

Trong quy trình Kỹ thuật Yêu cầu (*Requirements Engineering*), tài liệu mô tả bài toán từ khách hàng thường tồn tại dưới dạng văn bản tự nhiên phi cấu trúc (`.docx`, `.txt` hoặc đoạn văn thuần bằng **Tiếng Việt** hoặc **Tiếng Anh**).

**BA-Gen (ReqAssist-NLP)** đóng vai trò trợ lý thông minh cho Chuyên viên Phân tích Nghiệp vụ (BA) và Kỹ sư Yêu cầu, tự động hóa chuỗi quy trình:
1. **Đọc tài liệu đa định dạng & Tách câu nguyên tử:** Hỗ trợ `.docx` (đoạn văn + bảng biểu, $\le 25\text{ MB}$), `.txt` và dán văn bản trực tiếp. Chuẩn hóa Unicode `NFC`, xử lý thông minh chữ viết tắt (`VD.`, `e.g.`) và số thập phân (`99.9%`).
2. **Phân loại FR / NFR lai ghép (Hybrid):** Kết hợp học máy cục bộ `TF-IDF + LinearSVC` với cổng Multi-LLM (**Groq**, **OpenRouter**, **Gemini**, **Ollama**) kèm bộ nhớ đệm `SHA-256` SQLite và cơ chế tự động chuyển mạch dự phòng (*Circuit-Breaker Fallback* sang Offline ML trong $\le 2.0\text{ giây}$). Gán nhãn phụ NFR chuẩn **ISO/IEC 25010**.
3. **Phát hiện mơ hồ & Gợi ý chuẩn SMART:** Quét từ điển $\ge 120$ từ cảm tính song ngữ (*"nhanh chóng"*, *"thân thiện"*, *"fast"*, *"user-friendly"*), phát hiện thiếu Tác nhân (*Missing Actor*) và thiếu Số liệu đo lường (*Missing Metric*), đồng thời tự sinh câu viết lại chuẩn **SMART**.
4. **Sinh Agile User Stories & Gherkin AC:** Tự động sinh User Story theo chuẩn `Role - Goal - Benefit` kèm tối thiểu **2 kịch bản nghiệm thu Gherkin** (`GIVEN / WHEN / THEN`) cho luồng thành công và luồng ngoại lệ/biên.
5. **Xuất tài liệu SRS rút gọn & Sơ đồ Use Case:** Đóng gói tệp Word (`.docx`) và Markdown (`.md`) theo chuẩn **IEEE 830 / ISO 29148**, sinh mã PlantUML và kết xuất ảnh sơ đồ Use Case (`.png`/`.svg`) trực tiếp qua **Kroki API** (không cần cài Java hay Graphviz).
6. **Đánh giá Kiểm chuẩn (Benchmark):** Đo lường Accuracy, Precision, Recall, Macro F1-Score và Confusion Matrix 2×2 trên bộ 35 câu yêu cầu chuẩn.
7. **Đồng bộ sang Quản lý Dự án (Jira, GitHub Issues, Trello):** Hỗ trợ đẩy trực tiếp Agile User Stories và tiêu chí nghiệm thu Gherkin lên Jira Cloud, GitHub Issues và Trello Kanban Board qua REST API, hoặc xuất nhanh các tệp Import chuẩn hóa (Jira CSV, GitHub JSON, Trello JSON).

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy Nhanh (Quickstart Guide)

### 1. Yêu cầu Tiên quyết
- **Python:** Phiên bản `3.10` trở lên.
- **Git:** Đã cài đặt trên hệ điều hành.

### 2. Khởi tạo Môi trường Ảo

```bash
# Clone dự án (nếu chưa clone)
git clone https://github.com/nguyentrananhhoang13122005/BA-Gen.git
cd BA-Gen

# Tạo môi trường ảo Python
python -m venv .venv

# Kích hoạt môi trường ảo:
# Trên Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Trên Linux / macOS:
source .venv/bin/activate
```

### 3. Cài đặt Thư viện Phụ thuộc

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Thiết lập Biến Môi trường (.env)

Tạo tệp `.env` từ tệp mẫu `.env.example`:

```bash
cp .env.example .env
```

Cấu hình các khóa API mà bạn sử dụng (khuyến nghị dùng **Groq** vì tốc độ phản hồi cực nhanh $< 1\text{ giây}$):

```env
# Nhà cung cấp LLM mặc định: groq | openrouter | gemini | offline
DEFAULT_PROVIDER=groq

# Khóa API (Chỉ cần điền nhà cung cấp bạn sử dụng)
GROQ_API_KEY=gsk_your_groq_api_key_here
OPENROUTER_API_KEY=sk-or-your_openrouter_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Ngưỡng tin cậy kích hoạt chuyển tiếp LLM (0.50 - 0.95)
CONFIDENCE_THRESHOLD=0.75

# Đường dẫn cơ sở dữ liệu SQLite
DATABASE_PATH=reqassist.db
```

### 5. Khởi chạy Ứng dụng Web

```bash
streamlit run app.py
```
Ứng dụng sẽ tự động mở tại địa chỉ: `http://localhost:8501`.

### 6. Chạy Kiểm chuẩn (Benchmark) & Kiểm thử (Tests)

```bash
# Chạy bộ kiểm thử tự động
pytest

# Kiểm tra độ bao phủ mã nguồn (yêu cầu >= 85%)
pytest --cov=src --cov-report=term-missing

# Kiểm tra quy chuẩn mã nguồn PEP 8
flake8 src/ tests/
```

---

## 🏛️ Kiến trúc & Thiết kế Phần mềm

Hệ thống áp dụng kiến trúc **3-Tier Modular Monolith** cùng **5 mẫu thiết kế GoF chuẩn mực**:

1. **Strategy Pattern** (`src/classifiers/`): Đóng gói thuật toán phân loại độc lập (`ml_classifier`, `llm_classifier`, `hybrid_classifier`), cho phép chuyển đổi nóng giữa Offline ML và Multi-LLM API.
2. **Factory Method Pattern** (`src/parsers/`): `DocumentIngestionFactory` tự động chọn lớp đọc (`TxtDocumentParser`, `DocxDocumentParser`, `RawTextParser`) theo định dạng tệp.
3. **Facade Pattern** (`src/core/facade.py`): Lớp `RequirementAnalysisFacade` là điểm giao tiếp duy nhất giữa giao diện Streamlit và toàn bộ luồng xử lý phía sau.
4. **Builder Pattern** (`src/exporters/srs_builder.py`): Lắp ghép tuần tự 6 chương mục tài liệu SRS rút gọn trước khi kết xuất sang `.docx` / `.md`.
5. **Singleton Pattern** (`src/utils/lexicon.py`): Đảm bảo từ điển từ mơ hồ chỉ nạp vào bộ nhớ RAM đúng một lần.

Chi tiết xem tại: **[docs/ARCHITECTURE_AND_SPEC.md](docs/ARCHITECTURE_AND_SPEC.md)**.

---

## 📁 Cấu trúc Thư mục Dự án

```text
BA-Gen/
├── .github/
│   └── workflows/ci.yml           # Issue #17: CI/CD tự động chạy flake8 & pytest
├── data/
│   ├── ambiguity_lexicon.json     # Issue #3: Từ điển >= 120 từ mơ hồ song ngữ
│   ├── benchmark_35_reqs.json     # Issue #3: Bộ 35 câu kiểm chuẩn gán nhãn thủ công
│   └── sample_ecommerce_vi.*      # Issue #3: Tài liệu mẫu 1-click
├── docs/
│   ├── ARCHITECTURE_AND_SPEC.md   # Tài liệu Kiến trúc, Hợp đồng Dữ liệu & Đặc tả
│   └── IMPLEMENTATION_PLAN.md     # Kế hoạch 4 Sprints, 17 Issues & Kiểm thử
├── src/
│   ├── core/                      # Pydantic DTOs, SQLite & Facade điều phối
│   ├── parsers/                   # Factory đọc file docx/txt & tách câu nguyên tử
│   ├── classifiers/               # LinearSVC, Multi-LLM client & Benchmark
│   ├── analyzers/                 # Phát hiện từ mơ hồ & gợi ý viết lại SMART
│   ├── generators/                # Sinh Agile User Stories & Gherkin AC
│   ├── integrations/              # Tích hợp đồng bộ Jira Cloud, GitHub Issues & Trello
│   ├── exporters/                 # Xuất SRS (.docx/.md) & Sơ đồ PlantUML (Kroki API)
│   ├── ui/                        # Giao diện Streamlit (Sidebar & 4 Tabs Workbench)
│   └── utils/                     # Singleton quản lý từ điển & hàm tiện ích
├── tests/                         # Bộ kiểm thử đơn vị & tích hợp (Coverage >= 85%)
├── app.py                         # Điểm khởi chạy giao diện Web Streamlit
├── Dockerfile & docker-compose    # Đóng gói triển khai container
├── requirements.txt & .env.example# Cấu hình môi trường & thư viện phụ thuộc
├── .gitignore
└── README.md
```

---

## 🗺️ Lộ trình Triển khai (4 Sprints & 17 Issues)

- **Sprint 1 (Tuần 1–2):** Khởi tạo Dự án, Lược đồ Pydantic, SQLite Cache & Bộ dữ liệu kiểm chuẩn (*Issues #1 – #3*).
- **Sprint 2 (Tuần 3–4):** Đọc tài liệu đa định dạng & Phân loại FR/NFR lai ghép (*Issues #4 – #7*).
- **Sprint 3 (Tuần 5–6):** Bắt lỗi mơ hồ, sinh User Story + Gherkin, xuất SRS & Sơ đồ PlantUML (*Issues #8 – #13*).
- **Sprint 4 (Tuần 7–8):** Giao diện Streamlit hoàn chỉnh, Kiểm thử Pytest $\ge 85\%$, Docker & CI/CD (*Issues #14 – #17*).

Chi tiết kế hoạch từng Sprint xem tại: **[docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)**.
Theo dõi tiến độ 17 Issues trên GitHub: **[GitHub Issues List](https://github.com/nguyentrananhhoang13122005/BA-Gen/issues)**.

---

## 📄 Bản quyền & Tác giả
Dự án được xây dựng phục vụ nghiên cứu và thực hành Kỹ thuật Phần mềm (Requirements Engineering & NLP). Mọi đóng góp xin vui lòng tạo Pull Request hoặc mở Issue trên GitHub.
