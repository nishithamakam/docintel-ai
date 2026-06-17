"""
Word Document Parser — extracts text from .docx files.

Improvements:
1. Extracts BOTH paragraphs AND table content (tables hold key resume info)
2. Detects real page breaks (Word's <w:br type="page"/>) when present
3. Falls back to grouping ~10 paragraphs per "page" for finer citations
4. Preserves order: paragraphs and tables in document flow
"""
import os
from typing import List, Dict
from docx import Document
from docx.oxml.ns import qn


# How many paragraphs to group per "page" when no real page breaks are found
PARAGRAPHS_PER_PAGE = 10


def _iter_block_items(doc):
    """
    Yield paragraphs and tables in the order they appear in the document.
    python-docx's `doc.paragraphs` skips tables, so we walk the XML body.
    """
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table         import CT_Tbl
    from docx.text.paragraph     import Paragraph
    from docx.table              import Table

    body = doc.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)


def _has_page_break(paragraph) -> bool:
    """Detect if a paragraph contains a hard page break."""
    for run in paragraph.runs:
        for br in run._element.findall(qn("w:br")):
            if br.get(qn("w:type")) == "page":
                return True
    return False


def _table_to_text(table) -> str:
    """Convert a Word table into readable plain text."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def parse_docx(file_path: str) -> List[Dict]:
    """
    Parse a Word document into page-like sections.

    Returns:
        List of {"page_number": int, "text": str}

    Strategy:
        1. Walk through paragraphs + tables in order
        2. If a real page break is found, start a new page
        3. If no page breaks found, fall back to grouping every
           PARAGRAPHS_PER_PAGE paragraphs into one page
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = Document(file_path)

    pages           = []          # final list of {page_number, text}
    current_lines   = []          # lines collected for the current page
    current_page    = 1
    found_real_page_breaks = False

    def flush_page():
        """Save current_lines as a page and reset."""
        if current_lines:
            text = "\n".join(current_lines).strip()
            if text:
                pages.append({"page_number": current_page, "text": text})

    # ── Step 1: Walk through document, respect real page breaks ──
    from docx.text.paragraph import Paragraph
    from docx.table          import Table

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                current_lines.append(text)

            # Check for hard page break
            if _has_page_break(block):
                found_real_page_breaks = True
                flush_page()
                current_lines = []
                current_page += 1

        elif isinstance(block, Table):
            table_text = _table_to_text(block)
            if table_text:
                current_lines.append(table_text)

    # Flush the last page
    flush_page()

    # ── Step 2: If no real page breaks found, regroup into smaller "pages" ──
    if not found_real_page_breaks and pages:
        # Combine everything back, then split by paragraph count
        all_text = pages[0]["text"]
        all_lines = [line for line in all_text.split("\n") if line.strip()]

        if not all_lines:
            return [{"page_number": 1, "text": ""}]

        new_pages = []
        for i in range(0, len(all_lines), PARAGRAPHS_PER_PAGE):
            chunk_lines = all_lines[i : i + PARAGRAPHS_PER_PAGE]
            new_pages.append({
                "page_number": (i // PARAGRAPHS_PER_PAGE) + 1,
                "text":        "\n".join(chunk_lines),
            })
        pages = new_pages

    # Edge case: empty document
    if not pages:
        return [{"page_number": 1, "text": ""}]

    return pages


# ── Quick test ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "test.docx"
    pages = parse_docx(path)
    print(f"✅ Parsed {len(pages)} page(s)")
    for p in pages:
        preview = p["text"][:120].replace("\n", " ")
        print(f"  Page {p['page_number']}: {preview}...")
