"""Bộ nạp tài liệu đa định dạng (.txt, .docx, văn bản thô) theo Factory Method Pattern.

Đảm bảo an toàn tệp tin, chuẩn hóa Unicode NFC tiếng Việt, đọc cả văn bản
đoạn văn và bảng biểu trong tài liệu Microsoft Word.
"""

from abc import ABC, abstractmethod
import io
import os
import unicodedata
from typing import Union

from src.core.config import get_config


DISALLOWED_EXTENSIONS = {".exe", ".bat", ".docm", ".sh", ".cmd", ".vbs", ".msi"}


class IDocumentParser(ABC):
    """Giao diện trừu tượng cho tất cả các bộ phân tích tài liệu."""

    @abstractmethod
    def parse(self, source: Union[bytes, str]) -> str:
        """Đọc và trích xuất nội dung văn bản thuần đã chuẩn hóa NFC."""
        pass


class RawTextParser(IDocumentParser):
    """Trích xuất từ chuỗi văn bản thuần hoặc văn bản dán trực tiếp."""

    def parse(self, source: Union[bytes, str]) -> str:
        if isinstance(source, bytes):
            text = source.decode("utf-8", errors="replace")
        else:
            text = str(source)
        return unicodedata.normalize("NFC", text.strip())


class TxtDocumentParser(IDocumentParser):
    """Trích xuất từ tệp tin định dạng .txt (UTF-8, UTF-16)."""

    def parse(self, source: Union[bytes, str]) -> str:
        if isinstance(source, str):
            return unicodedata.normalize("NFC", source.strip())

        # Thử giải mã lần lượt qua UTF-8, sau đó UTF-16
        for enc in ["utf-8", "utf-16", "utf-8-sig", "latin-1"]:
            try:
                decoded = source.decode(enc)
                return unicodedata.normalize("NFC", decoded.strip())
            except UnicodeDecodeError:
                continue

        decoded = source.decode("utf-8", errors="replace")
        return unicodedata.normalize("NFC", decoded.strip())


class DocxDocumentParser(IDocumentParser):
    """Trích xuất văn bản từ tệp Word .docx bao gồm paragraphs và tables."""

    def parse(self, source: Union[bytes, str]) -> str:
        try:
            import docx
        except ImportError:
            raise ImportError("Thư viện 'python-docx' chưa được cài đặt.")

        if isinstance(source, bytes):
            stream = io.BytesIO(source)
            doc = docx.Document(stream)
        elif isinstance(source, str) and os.path.exists(source):
            doc = docx.Document(source)
        else:
            raise ValueError("Đầu vào DocxDocumentParser phải là bytes hoặc đường dẫn tệp hợp lệ.")

        extracted_lines = []

        table_header_markers = {
            "mã fr", "mô tả yêu cầu chi tiết", "độ ưu tiên",
            "vai trò (role)", "mô tả & phạm vi quyền hạn chính",
            "stt", "requirement id", "priority",
        }
        priority_suffixes = {
            "cao (high)", "cao(high)", "trung bình (medium)", "trung bình(medium)",
            "thấp (low)", "thấp(low)", "high", "medium", "low", "cao", "trung bình", "thấp",
        }

        def _process_table(table_obj):
            for row in table_obj.rows:
                row_texts = [
                    " ".join(cell.text.split())
                    for cell in row.cells
                    if cell.text and cell.text.strip()
                ]
                unique_cells = list(dict.fromkeys(row_texts))
                if not unique_cells:
                    continue

                joined_lower = " | ".join(unique_cells).lower()
                # Bỏ qua bảng bìa tài liệu (Cover Table)
                if (
                    ("tài liệu phân tích nghiệp vụ" in joined_lower and "phiên bản" in joined_lower)
                    or ("mã dự án" in joined_lower and "ngôn ngữ" in joined_lower)
                ):
                    continue
                # Bỏ qua dòng tiêu đề bảng (Table Header Row)
                if sum(1 for m in table_header_markers if m in joined_lower) >= 2:
                    continue

                if len(unique_cells) >= 3 and unique_cells[-1].lower() in priority_suffixes:
                    unique_cells = unique_cells[:-1]

                merged_row = " — ".join(unique_cells).replace(". ", "; ")
                extracted_lines.append(merged_row)

        # Đọc paragraphs và tables theo đúng thứ tự xuất hiện từ trên xuống dưới trong tài liệu Word
        from docx.oxml.table import CT_Tbl
        from docx.oxml.text.paragraph import CT_P
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        for child in doc.element.body.iterchildren():
            if isinstance(child, CT_P):
                p = Paragraph(child, doc)
                text = p.text.strip()
                if text:
                    extracted_lines.append(text)
            elif isinstance(child, CT_Tbl):
                t = Table(child, doc)
                _process_table(t)

        full_text = "\n".join(extracted_lines)
        return unicodedata.normalize("NFC", full_text.strip())


class DocumentIngestionFactory:
    """Lớp Factory Method tạo đối tượng bộ đọc tài liệu phù hợp."""

    @staticmethod
    def create_parser(filename: str, file_size_bytes: int = 0) -> IDocumentParser:
        max_bytes = get_config().max_file_size_bytes
        if file_size_bytes > max_bytes:
            raise ValueError(
                f"Tệp quá lớn ({file_size_bytes / (1024 * 1024):.1f} MB). "
                f"Giới hạn dung lượng tối đa là {max_bytes / (1024 * 1024):.0f} MB."
            )

        _, ext = os.path.splitext(filename.lower())

        if ext in DISALLOWED_EXTENSIONS:
            raise ValueError(f"Định dạng tệp không được phép: {ext}")

        if ext == ".docx":
            return DocxDocumentParser()
        elif ext in [".txt", ".text"]:
            return TxtDocumentParser()
        elif ext == "" or ext in [".raw", ".md"]:
            return RawTextParser()
        else:
            raise ValueError(f"Định dạng tệp '{ext}' không được hỗ trợ. Vui lòng tải .docx, .txt hoặc dán trực tiếp.")
