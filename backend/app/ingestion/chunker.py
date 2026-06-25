"""
Chunker - Splits page text into overlapping token-based chunks.

Why token-based (not character-based)?
- LLMs measure input in tokens, not characters
- Token-based chunking gives predictable LLM costs
- Tokens are roughly: 1 token ≈ 4 characters in English

Why overlapping chunks?
- Prevents losing meaning at chunk boundaries
- Each chunk has full context even if a sentence spans two chunks
"""
import tiktoken
from typing import List, Dict
from app.config import settings

# Load the tokenizer once at module load (it's expensive to create)
# "cl100k_base" is the tokenizer used by GPT-4, GPT-3.5, and embedding models
encoder = tiktoken.get_encoding("cl100k_base")


def chunk_pages(pages: List[Dict], doc_id: str, doc_name: str) -> List[Dict]:
    """
    Convert a list of pages into overlapping chunks ready for embedding.

    Args:
        pages: Output from parse_pdf() - list of {page_number, text, char_count}
        doc_id: Unique ID for this document (e.g., "abc12345")
        doc_name: Original filename (e.g., "Policy.pdf") - used in citations

    Returns:
        A list of chunks, each containing:
        - chunk_id: Unique ID for this chunk
        - doc_id: Which document this chunk belongs to
        - doc_name: Original filename (for citations)
        - page_number: Which page this chunk came from
        - text: The actual chunk text
        - token_count: Number of tokens in this chunk

    Example return value:
        [
            {
                "chunk_id": "abc12345_0",
                "doc_id": "abc12345",
                "doc_name": "Policy.pdf",
                "page_number": 1,
                "text": "Refunds are allowed...",
                "token_count": 750
            },
            ...
        ]
    """
    chunks = []
    chunk_index = 0  # Counter for unique chunk IDs within this document

    # Calculate the "stride" — how far we move forward each iteration
    # If chunk_size=800 and overlap=100, stride=700 (we advance 700 tokens each time)
    stride = settings.chunk_size - settings.chunk_overlap

    # Process each page separately
    # This is intentional — we DON'T let chunks span across pages
    # Why? Because each chunk needs a single page number for citations
    for page in pages:
        # Convert this page's text into tokens
        tokens = encoder.encode(page["text"])

        # Slide a window across the tokens
        # range(start, stop, step) — we step forward by `stride` each time
        for start in range(0, len(tokens), stride):
            # Grab a window of `chunk_size` tokens
            window = tokens[start : start + settings.chunk_size]

            # Skip very small leftover chunks (< 50 tokens)
            # These are usually just trailing fragments with no real content
            if len(window) < 50:
                continue

            # Convert tokens back to text
            text = encoder.decode(window)

            # Build the chunk dictionary
            chunks.append({
                "chunk_id": f"{doc_id}_{chunk_index}",
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page_number": page["page_number"],
                "section_kind": page.get("section_kind", "page"),
                "text": text,
                "token_count": len(window),
            })

            chunk_index += 1

    return chunks


# Quick test when running this file directly
if __name__ == "__main__":
    import sys
    from app.ingestion.pdf_parser import parse_pdf

    if len(sys.argv) < 2:
        print("Usage: python -m app.ingestion.chunker <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"📄 Parsing: {pdf_path}")

    # Step 1: Parse the PDF
    pages = parse_pdf(pdf_path)
    print(f"✅ Extracted {len(pages)} pages\n")

    # Step 2: Chunk it
    chunks = chunk_pages(pages, doc_id="test123", doc_name="test.pdf")
    print(f"✂️  Created {len(chunks)} chunks\n")

    # Show stats
    total_tokens = sum(c["token_count"] for c in chunks)
    print(f"📊 Total tokens across all chunks: {total_tokens}")
    print(f"📊 Average tokens per chunk: {total_tokens // len(chunks)}\n")

    # Show first 2 chunks as preview
    for c in chunks[:2]:
        print(f"--- {c['chunk_id']} (page {c['page_number']}, {c['token_count']} tokens) ---")
        print(c['text'][:300])
        print()
