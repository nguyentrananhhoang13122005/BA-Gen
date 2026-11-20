"""Bộ kiểm thử cho Document Parsers và DocumentIngestionFactory."""

import io
import docx
import pytest
from src.parsers.factory import (
    DocumentIngestionFactory,
    DocxDocumentParser,
    RawTextParser,
    TxtDocumentParser,
    MAX_FILE_SIZE_BYTES
)


def test_raw_text_parser():
    parser = RawTextParser()
    text = "Hệ thống cho phép đăng ký tài khoản."
    result = parser.parse(text)
    assert "đăng ký" in result

    b_text = text.encode("utf-8")
    assert parser.parse(b_text) == text


def test_txt_document_parser():
    parser = TxtDocumentParser()
    raw = "The system shall encrypt passwords.\nSecond line."
    b_raw = raw.encode("utf-8")
    result = parser.parse(b_raw)
    assert "encrypt passwords" in result


def test_docx_document_parser():
    doc = docx.Document()
    doc.add_paragraph("Người dùng có thể tìm kiếm sản phẩm.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "REQ-01"
    table.rows[0].cells[1].text = "Hỗ trợ thanh toán VNPAY"

    buf = io.BytesIO()
    doc.save(buf)
    content = buf.getvalue()

    parser = DocxDocumentParser()
    parsed_text = parser.parse(content)
    assert "tìm kiếm sản phẩm" in parsed_text
    assert "Hỗ trợ thanh toán VNPAY" in parsed_text


def test_factory_creates_correct_parser():
    txt_parser = DocumentIngestionFactory.create_parser("requirements.txt")
    assert isinstance(txt_parser, TxtDocumentParser)

    docx_parser = DocumentIngestionFactory.create_parser("spec.docx")
    assert isinstance(docx_parser, DocxDocumentParser)

    raw_parser = DocumentIngestionFactory.create_parser("pasted.raw")
    assert isinstance(raw_parser, RawTextParser)


def test_factory_rejects_disallowed_extensions():
    with pytest.raises(ValueError, match="Định dạng tệp không được phép"):
        DocumentIngestionFactory.create_parser("malware.exe")

    with pytest.raises(ValueError, match="Định dạng tệp không được phép"):
        DocumentIngestionFactory.create_parser("script.bat")


def test_factory_rejects_oversized_files():
    oversized = MAX_FILE_SIZE_BYTES + 1024
    with pytest.raises(ValueError, match="Tệp quá lớn"):
        DocumentIngestionFactory.create_parser("huge.docx", file_size_bytes=oversized)
