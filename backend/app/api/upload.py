"""
Upload endpoint — accepts PDF or Word (.docx) files,
runs the full ingestion pipeline, stores in FAISS.
"""
import os
import uuid
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.ingestion.pdf_parser  import parse_pdf
from app.ingestion.docx_parser import parse_docx
from app.ingestion.chunker     import chunk_pages
from app.ingestion.embedder    import embed_texts
from app.storage.vector_store  import store

router = APIRouter()

# Supported file types
SUPPORTED_TYPES = {
    "application/pdf":                                                      "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword":                                                   "docx",
}
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}


# ── Response model ────────────────────────────────────────────────────────────
class UploadResponse(BaseModel):
    doc_id:   str
    filename: str
    file_type: str
    pages:    int
    chunks:   int
    message:  str


# ── Endpoint ──────────────────────────────────────────────────────────────────
@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a PDF or Word document.

    Pipeline:
        1. Validate file type
        2. Save to disk
        3. Parse into pages
        4. Chunk pages into overlapping text windows
        5. Embed chunks
        6. Store in FAISS
        7. Return summary
    """

    # ── Step 1: Validate ──────────────────────────────────────────────────────
    filename  = file.filename or ""
    ext       = os.path.splitext(filename)[1].lower()

    # Detect type from extension (more reliable than content-type from browser)
    if ext == ".pdf":
        file_type = "pdf"
    elif ext in (".docx", ".doc"):
        file_type = "docx"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Please upload a PDF or Word (.docx) file.",
        )

    # ── Step 2: Save to disk ──────────────────────────────────────────────────
    doc_id    = str(uuid.uuid4())[:8]
    save_dir  = settings.upload_dir
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{doc_id}_{filename}")

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # ── Step 3: Parse ─────────────────────────────────────────────────────────
    try:
        if file_type == "pdf":
            pages = parse_pdf(save_path)
        else:
            pages = parse_docx(save_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {e}")

    if not pages:
        raise HTTPException(status_code=400, detail="Document appears to be empty.")

    # ── Step 4: Chunk ─────────────────────────────────────────────────────────
    doc_name = filename
    chunks   = chunk_pages(pages, doc_id=doc_id, doc_name=doc_name)

    if not chunks:
        raise HTTPException(status_code=400, detail="No text content found in document.")

    # ── Step 5 & 6: Embed + Store ─────────────────────────────────────────────
    texts      = [c["text"]      for c in chunks]
    embeddings = embed_texts(texts)
    store.add(embeddings, chunks)

    # ── Step 7: Return summary ────────────────────────────────────────────────
    return UploadResponse(
        doc_id    = doc_id,
        filename  = filename,
        file_type = file_type.upper(),
        pages     = len(pages),
        chunks    = len(chunks),
        message   = f"✅ Successfully processed {filename}",
    )
