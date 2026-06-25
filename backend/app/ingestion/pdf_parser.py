"""
PDF Parser - Extracts text from PDF files page by page.

Uses PyMuPDF (fitz) which is fast, accurate, and preserves layout.
We extract text per-page so we can cite page numbers in answers later.
"""
import fitz  # PyMuPDF library
from typing import List, Dict


def parse_pdf(file_path: str) -> List[Dict]:
    """
    Read a PDF file and return text from each page.

    Args:
        file_path: Path to the PDF file (e.g., "data/uploads/report.pdf")

    Returns:
        A list of dictionaries, one per page, each containing:
        - page_number: int (1-indexed, matches what users see)
        - text: str (the actual text content of that page)
        - char_count: int (length of the text, useful for stats)

    Example return value:
        [
            {"page_number": 1, "text": "Introduction...", "char_count": 1245},
            {"page_number": 2, "text": "Methods...", "char_count": 890},
        ]
    """
    # Open the PDF file
    doc = fitz.open(file_path)

    pages = []

    # Loop through every page in the document
    # enumerate() gives us (index, page) — index starts at 0
    for i, page in enumerate(doc):
        # Extract plain text from this page
        text = page.get_text("text")

        # Skip pages that are empty or only whitespace
        # (e.g., blank cover pages, separator pages)
        if text.strip():
            pages.append({
                "page_number": i + 1,  # +1 because humans count from 1, not 0
                "text": text,
                "char_count": len(text),
                "section_kind": "page"
            })

    # Always close the file when done — releases memory
    doc.close()

    return pages


# Quick test when running this file directly
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"📄 Parsing: {pdf_path}\n")

    pages = parse_pdf(pdf_path)

    print(f"✅ Extracted {len(pages)} non-empty pages\n")
    for p in pages[:3]:  # show first 3 pages only
        print(f"--- Page {p['page_number']} ({p['char_count']} chars) ---")
        print(p['text'][:300])  # first 300 chars
        print()
