from pathlib import Path


def extract_text(file_path: str) -> tuple[str, int]:
    """Returns (text, page_count)."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix in (".docx",):
        text = _extract_docx(file_path)
        return text, 0
    if suffix == ".txt":
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        return text, 0
    raise ValueError(f"Unsupported file type: {suffix}")


def _extract_pdf(path: str) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    page_count = len(reader.pages)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip()), page_count


def _extract_docx(path: str) -> str:
    from docx import Document

    doc = Document(path)
    return "\n\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
