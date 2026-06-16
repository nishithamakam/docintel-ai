"""
Upload Endpoint - Accepts PDF files and processes them into the vector store.

Flow:
    1. Receive PDF file from user
    2. Validate it's actually a PDF
    3. Save to disk with a unique ID
    4. Parse → Chunk → Embed → Store
    5. Return summary of what was processed

This is the "ingestion" phase of RAG — turning raw documents
into searchable knowledge.
"""
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.config import DATA_DIR, settings
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.chunker import chunk_pages
from app.ingestion.embedder import embed_texts
from app.storage.vector_store import store

# APIRouter is like a mini FastAPI app
# We collect related endpoints in a router, then attach to main app
router = APIRouter()


# ── Response Model ──────────────────────────────────────────
# Pydantic model defining what our endpoint returns
# This auto-generates API docs and validates our output
class UploadResponse(BaseModel):
    doc_id: str           # Unique ID for this document
    filename: str         # Original filename
    pages: int            # Number of non-empty pages found
    chunks: int           # Number of chunks created
    message: str          # Human-friendly summary


# ── Upload Endpoint ──────────────────────────────────────────
@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a PDF document",
    description="Upload a PDF file to be parsed, chunked, embedded and stored for Q&A",
)
async def upload_pdf(
    file: UploadFile = File(..., description="A PDF file to upload"),
):
    """
    Upload and process a PDF file.

    Steps performed:
    1. Validate file is a PDF
    2. Save to uploads folder with unique ID
    3. Parse PDF into pages
    4. Split pages into overlapping chunks
    5. Generate embeddings for each chunk
    6. Store embeddings + metadata in FAISS vector store
    """

    # ── Step 1: Validate file type ───────────────────────────
    # We check both the filename extension AND the content type
    # Users can rename files, so we check both for safety
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file."
        )

    # ── Step 2: Generate unique document ID ─────────────────
    # uuid4() generates a random unique identifier like "a3f2c1d4-..."
    # We take the first 8 characters for brevity (still unique enough)
    doc_id = str(uuid.uuid4())[:8]

    # Build the save path: data/uploads/abc12345_MyDoc.pdf
    # We prefix with doc_id so files with the same name don't overwrite each other
    safe_filename = f"{doc_id}_{file.filename}"
    save_path = DATA_DIR / "uploads" / safe_filename

    # ── Step 3: Save file to disk ────────────────────────────
    # We read the uploaded file in chunks and write to disk
    # This is memory-efficient for large files
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )
    finally:
        # Always close the uploaded file to free resources
        await file.close()

    # ── Step 4: Parse PDF ────────────────────────────────────
    try:
        pages = parse_pdf(str(save_path))
    except Exception as e:
        # If parsing fails, clean up the saved file
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse PDF: {str(e)}"
        )

    if not pages:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="No readable text found in this PDF. It may be scanned/image-based."
        )

    # ── Step 5: Chunk pages ──────────────────────────────────
    chunks = chunk_pages(
        pages=pages,
        doc_id=doc_id,
        doc_name=file.filename,  # original name for citations
    )

    if not chunks:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="Could not create chunks from this PDF."
        )

    # ── Step 6: Generate embeddings ──────────────────────────
    try:
        texts = [chunk["text"] for chunk in chunks]
        vectors = embed_texts(texts)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings: {str(e)}"
        )

    # ── Step 7: Store in vector store ───────────────────────
    try:
        store.add(vectors, chunks)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store embeddings: {str(e)}"
        )

    # ── Step 8: Return summary ───────────────────────────────
    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        pages=len(pages),
        chunks=len(chunks),
        message=f"✅ Successfully processed '{file.filename}': {len(pages)} pages, {len(chunks)} chunks stored and ready for Q&A.",
    )
