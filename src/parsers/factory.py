"""Bộ nạp tài liệu đa định dạng (.txt, .docx, văn bản thô) theo Factory Method Pattern.

Đảm bảo an toàn tệp tin, chuẩn hóa Unicode NFC tiếng Việt, đọc cả văn bản
đoạn văn và bảng biểu trong tài liệu Microsoft Word.
"""

from abc import ABC, abstractmethod
import io
import os
import unicodedata
from typing import Union


MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
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

        # 1. Đọc các đoạn văn (paragraphs)
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                extracted_lines.append(text)

        # 2. Đọc nội dung từ các bảng biểu (tables)
        for table in doc.tables:
            for row in table.rows:
                row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_texts:
                    # Gộp các ô trong cùng dòng thành một câu mô tả yêu cầu
                    extracted_lines.append(" - ".join(dict.fromkeys(row_texts)))

        full_text = "\n".join(extracted_lines)
        return unicodedata.normalize("NFC", full_text.strip())


class DocumentIngestionFactory:
    """Lớp Factory Method tạo đối tượng bộ đọc tài liệu phù hợp."""

    @staticmethod
    def create_parser(filename: str, file_size_bytes: int = 0) -> IDocumentParser:
        if file_size_bytes > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Tệp quá lớn ({file_size_bytes / (1024 * 1024):.1f} MB). "
                f"Giới hạn dung lượng tối đa là 25 MB."
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
