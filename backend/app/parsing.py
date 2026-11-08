import csv
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document as WordDocument
from pypdf import PdfReader

SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".csv": "text/csv",
}


@dataclass
class ExtractedPage:
    page_number: int | None
    text: str


def validate_file(filename: str, content: bytes, max_upload_mb: int) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise ValueError("Supported file types are PDF, DOCX, TXT, and CSV.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > max_upload_mb * 1024 * 1024:
        raise ValueError(f"File exceeds the {max_upload_mb} MB upload limit.")
    if suffix == ".pdf" and not content.lstrip().startswith(b"%PDF-"):
        raise ValueError("The file does not have a valid PDF signature.")
    if suffix == ".docx" and not content.startswith(b"PK\x03\x04"):
        raise ValueError("The file does not have a valid DOCX signature.")
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members = archive.infolist()
                if len(members) > 5000 or sum(member.file_size for member in members) > 200 * 1024 * 1024:
                    raise ValueError("The DOCX archive expands beyond the supported processing limit.")
                if any(member.flag_bits & 0x1 for member in members):
                    raise ValueError("Encrypted DOCX files are not supported.")
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("The DOCX archive does not contain a document body.")
        except zipfile.BadZipFile as exc:
            raise ValueError("The file is not a valid DOCX archive.") from exc
    if suffix in {".txt", ".csv"} and b"\x00" in content[:8192]:
        raise ValueError("The file does not appear to be plain text.")
    try:
        content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        if suffix in {".txt", ".csv"}:
            raise ValueError("Text and CSV files must use UTF-8 encoding.") from exc
    return suffix, SUPPORTED_TYPES[suffix]


def extract_text(path: Path, suffix: str) -> list[ExtractedPage]:
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        result = [ExtractedPage(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
    elif suffix == ".docx":
        doc = WordDocument(str(path))
        pieces = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                pieces.append(" | ".join(cell.text.strip() for cell in row.cells))
        result = [ExtractedPage(None, "\n".join(pieces))]
    elif suffix == ".csv":
        text = path.read_text(encoding="utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        result = [ExtractedPage(None, "\n".join(" | ".join(cell.strip() for cell in row) for row in rows))]
    else:
        result = [ExtractedPage(None, path.read_text(encoding="utf-8-sig"))]
    cleaned = []
    for item in result:
        normalized = re.sub(r"[\t\u00a0 ]+", " ", item.text)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
        if normalized:
            cleaned.append(ExtractedPage(item.page_number, normalized))
    if not cleaned:
        raise ValueError("No extractable text was found. Scanned PDFs require OCR, which is not included.")
    return cleaned


def chunk_pages(pages: list[ExtractedPage], size: int, overlap: int) -> list[ExtractedPage]:
    chunks: list[ExtractedPage] = []
    size = max(size, 200)
    overlap = min(max(overlap, 0), size // 2)
    for page in pages:
        text = page.text
        if len(text) <= size:
            chunks.append(page)
            continue
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = max(text.rfind("\n", start + size // 2, end), text.rfind(". ", start + size // 2, end))
                if boundary > start:
                    end = boundary + 1
            excerpt = text[start:end].strip()
            if excerpt:
                chunks.append(ExtractedPage(page.page_number, excerpt))
            if end >= len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks

