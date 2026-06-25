"""
Upload endpoint — accepts many file types, runs ingestion pipeline.
Supports: PDF, Word, PowerPoint, and plain-text formats.
"""
import os
import uuid
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.ingestion.pdf_parser  import parse_pdf
from app.ingestion.docx_parser import parse_docx
from app.ingestion.text_parser import parse_text_file, parse_pptx
from app.ingestion.chunker     import chunk_pages
from app.ingestion.embedder    import embed_texts
from app.storage.vector_store  import store

router = APIRouter()

# Map extensions to parser type
PDF_EXTS  = {".pdf"}
DOCX_EXTS = {".docx", ".doc"}
PPTX_EXTS = {".pptx", ".ppt"}
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".log", ".py",
             ".js", ".html", ".xml", ".yaml", ".yml", ".rtf"}


class UploadResponse(BaseModel):
    doc_id:    str
    filename:  str
    file_type: str
    pages:     int
    chunks:    int
    message:   str


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    # Determine parser
    if ext in PDF_EXTS:
        file_type = "PDF"
    elif ext in DOCX_EXTS:
        file_type = "Word"
    elif ext in PPTX_EXTS:
        file_type = "PowerPoint"
    elif ext in TEXT_EXTS:
        file_type = "Text"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: PDF, Word, "
                   f"PowerPoint, and text files (.txt, .md, .csv, .json, etc.)",
        )

    # Save to disk
    doc_id   = str(uuid.uuid4())[:8]
    save_dir = settings.upload_dir
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{doc_id}_{filename}")

    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Parse
    try:
        if file_type == "PDF":
            pages = parse_pdf(save_path)
        elif file_type == "Word":
            pages = parse_docx(save_path)
        elif file_type == "PowerPoint":
            pages = parse_pptx(save_path)
        else:
            pages = parse_text_file(save_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {e}")

    if not pages:
        raise HTTPException(status_code=400, detail="Document appears to be empty.")

    # Chunk
    chunks = chunk_pages(pages, doc_id=doc_id, doc_name=filename)
    if not chunks:
        raise HTTPException(status_code=400, detail="No text content found in document.")

    # Embed + store
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    store.add(embeddings, chunks)

    return UploadResponse(
        doc_id    = doc_id,
        filename  = filename,
        file_type = file_type,
        pages     = len(pages),
        chunks    = len(chunks),
        message   = f"Successfully processed {filename}",
    )
