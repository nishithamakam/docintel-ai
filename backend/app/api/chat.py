"""
Chat endpoint — receives a question, retrieves relevant chunks,
calls GPT, returns a grounded answer with citations.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from app.config import settings
from app.ingestion.embedder import embed_texts
from app.storage.vector_store import store

router = APIRouter()


# ── Request / Response models ─────────────────────────────────────────────────
class Message(BaseModel):
    role: str      # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    question:  str
    history:   Optional[List[Message]] = []
    doc_ids:   Optional[List[str]]     = None   # filter to specific docs
    min_score: float                   = 0.25   # relevance threshold


class SourceChunk(BaseModel):
    doc_name: str
    page:     int
    snippet:  str
    score:    float


class ChatResponse(BaseModel):
    answer:       str
    sources:      List[SourceChunk]
    chunks_found: int


# ── Endpoint ──────────────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    1. Embed the question
    2. Search FAISS (with optional doc filter + score threshold)
    3. Build a grounded prompt
    4. Call GPT
    5. Return answer + citations
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    # ── Step 1: Embed the question ────────────────────────────────────────────
    query_vector = embed_texts([req.question])

    # ── Step 2: Retrieve relevant chunks ─────────────────────────────────────
    chunks = store.search(
        query_vector,
        k=settings.top_k,
        doc_ids=req.doc_ids,
        min_score=req.min_score,
    )

    # ── Step 3: Build context from retrieved chunks ───────────────────────────
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Source {i}: {chunk['doc_name']}, Page {chunk['page_number']}]\n"
                f"{chunk['text']}"
            )

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = (
            "You are a helpful document assistant. "
            "Answer the user's question using ONLY the provided document excerpts. "
            "Always cite your sources as (Source N, Page X). "
            "If the answer is not in the excerpts, say so clearly.\n\n"
            f"Document excerpts:\n\n{context}"
        )
    else:
        system_prompt = (
            "You are a helpful document assistant. "
            "No relevant document excerpts were found for this question. "
            "Politely tell the user you couldn't find relevant information "
            "in the uploaded documents."
        )

    # ── Step 4: Build message history for GPT ────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]

    for msg in (req.history or []):
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": req.question})

    # ── Step 5: Call GPT ──────────────────────────────────────────────────────
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=messages,
        max_completion_tokens=1024,
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    # ── Step 6: Build source list for frontend ────────────────────────────────
    sources = [
        SourceChunk(
            doc_name=c["doc_name"],
            page=c["page_number"],
            snippet=c["text"][:300],
            score=round(c["score"], 4),
        )
        for c in chunks
    ]

    return ChatResponse(
        answer=answer,
        sources=sources,
        chunks_found=len(chunks),
    )
