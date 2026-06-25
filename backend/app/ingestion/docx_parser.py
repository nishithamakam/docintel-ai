"""
Word Document Parser.

Strategy:
    1. Convert .docx → .pdf using Microsoft Word (real page breaks!)
    2. Parse the PDF with PyMuPDF for ACCURATE page numbers
    3. If conversion fails, fall back to paragraph-grouping
"""
import os
import tempfile
from typing import List, Dict


def parse_docx(file_path: str) -> List[Dict]:
    """Parse a Word document into pages with accurate page numbers."""
    # Try the high-quality path first: convert to PDF, then parse
    try:
        return _parse_via_pdf(file_path)
    except Exception as e:
        print(f"⚠️  docx→PDF conversion failed ({e}); using fallback parser")
        return _parse_fallback(file_path)


def _parse_via_pdf(file_path: str) -> List[Dict]:
    """Convert docx → pdf with Word, then parse for real page numbers."""
    from docx2pdf import convert
    from app.ingestion.pdf_parser import parse_pdf

    # Create a temp PDF path
    tmp_dir  = tempfile.gettempdir()
    base     = os.path.splitext(os.path.basename(file_path))[0]
    pdf_path = os.path.join(tmp_dir, f"{base}_converted.pdf")

    # Convert (uses installed Microsoft Word)
    convert(file_path, pdf_path)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF was not created")

    # Parse the PDF for accurate page numbers
    pages = parse_pdf(pdf_path)

    # Tag as real pages
    for p in pages:
        p["section_kind"] = "page"

    # Clean up temp file
    try:
        os.remove(pdf_path)
    except Exception:
        pass

    return pages


# ── Fallback: paragraph grouping (no real pages) ──────────────
PARAGRAPHS_PER_PAGE = 10


def _parse_fallback(file_path: str) -> List[Dict]:
    """Fallback parser when PDF conversion isn't available."""
    from docx import Document
    from docx.oxml.ns import qn

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = Document(file_path)

    def table_to_text(table):
        rows = []
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                rows.append(" | ".join(cells))
        return "\n".join(rows)

    # Collect all text (paragraphs + tables) in order
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table         import CT_Tbl
    from docx.text.paragraph     import Paragraph
    from docx.table              import Table

    lines = []
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            text = Paragraph(child, doc).text.strip()
            if text:
                lines.append(text)
        elif isinstance(child, CT_Tbl):
            t = table_to_text(Table(child, doc))
            if t:
                lines.append(t)

    if not lines:
        return [{"page_number": 1, "text": "", "section_kind": "section"}]

    pages = []
    for i in range(0, len(lines), PARAGRAPHS_PER_PAGE):
        chunk = lines[i : i + PARAGRAPHS_PER_PAGE]
        pages.append({
            "page_number": (i // PARAGRAPHS_PER_PAGE) + 1,
            "text": "\n".join(chunk),
            "section_kind": "section",
        })
    return pages
