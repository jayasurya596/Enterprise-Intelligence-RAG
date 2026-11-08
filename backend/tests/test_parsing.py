from io import BytesIO
from pathlib import Path

import pytest
from docx import Document as WordDocument

from app.parsing import chunk_pages, extract_text, validate_file


def test_rejects_fake_pdf_signature():
    with pytest.raises(ValueError, match="signature"):
        validate_file("report.pdf", b"not a pdf", 25)


def test_extracts_text_and_keeps_chunks_nonempty(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("Heading\n\n" + "A useful sentence. " * 80, encoding="utf-8")
    pages = extract_text(path, ".txt")
    chunks = chunk_pages(pages, size=300, overlap=40)
    assert chunks
    assert all(part.text.strip() for part in chunks)
    assert chunks[0].text.startswith("Heading")


def test_rejects_empty_text_file():
    path = Path("empty.txt")
    with pytest.raises(ValueError, match="empty"):
        validate_file(path.name, b"", 25)


def test_extracts_csv(tmp_path: Path):
    path = tmp_path / "table.csv"
    path.write_text("Name,Status\nRaven,Active\n", encoding="utf-8")
    extracted = extract_text(path, ".csv")
    assert "Raven | Active" in extracted[0].text


def test_extracts_docx(tmp_path: Path):
    path = tmp_path / "brief.docx"
    doc = WordDocument()
    doc.add_paragraph("A verified Word paragraph.")
    doc.save(path)
    extracted = extract_text(path, ".docx")
    assert extracted[0].page_number is None
    assert "verified Word paragraph" in extracted[0].text


def make_text_pdf() -> bytes:
    content = b"BT /F1 12 Tf 50 700 Td (Hello from a parsed PDF.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def test_extracts_pdf_and_preserves_page_number(tmp_path: Path):
    path = tmp_path / "brief.pdf"
    path.write_bytes(make_text_pdf())
    extracted = extract_text(path, ".pdf")
    assert extracted[0].page_number == 1
    assert "Hello from a parsed PDF" in extracted[0].text

