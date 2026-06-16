"""
Chat Endpoint - The core RAG question-answering engine.

Flow:
    1. Receive user's question + conversation history
    2. Embed the question into a vector
    3. Search FAISS for most relevant chunks
    4. Build a prompt with those chunks as context
    5. Send to GPT → get grounded answer with citations
    6. Return answer + sources to the user
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from openai import OpenAI

from app.config import settings
from app.ingestion.embedder import embed_one
from app.storage.vector_store import store

router = APIRouter()

# Create OpenAI client pointed at BMS gateway
client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

# ── Request & Response Models ────────────────────────────────

class Message(BaseModel):
    """A single message in the conversation history."""
    role: str     # "user" or "assistant"
    content: str  # The message text


class ChatRequest(BaseModel):
    """What the frontend sends us."""
    question: str                    # Current user question
    history: Optional[List[Message]] = []  # Previous messages for context


class SourceChunk(BaseModel):
    """A source document chunk returned with the answer."""
    doc_name: str    # Original filename
    page: int        # Page number
    snippet: str     # First 300 chars of the chunk
    score: float     # Relevance score (0-1)


class ChatResponse(BaseModel):
    """What we send back to the frontend."""
    answer: str                  # GPT's answer
    sources: List[SourceChunk]   # Supporting document chunks
    chunks_found: int            # How many chunks were retrieved


# ── System Prompt ────────────────────────────────────────────
# This tells GPT exactly how to behave
SYSTEM_PROMPT = """You are DocIntel AI — an expert enterprise document assistant.

Your job is to answer questions STRICTLY based on the provided document context.

RULES:
1. ONLY use information from the provided context chunks.
2. For EVERY factual claim, add an inline citation like: [Source: filename.pdf, p.X]
3. If the context doesn't contain enough information, say:
   "I couldn't find enough information about this in the uploaded documents."
4. NEVER make up information or use knowledge outside the provided context.
5. Be concise but complete. Use bullet points for lists.
6. If multiple documents are relevant, cite all of them.

FORMAT your answer like this:
- Give a clear direct answer first
- Add citations inline: [Source: doc.pdf, p.3]
- End with a brief summary if the answer is long
"""


# ── Helper: Build context from chunks ───────────────────────
def build_context(chunks: List[dict]) -> str:
    """
    Format retrieved chunks into a readable context block for GPT.

    Each chunk is formatted with its source info so GPT can cite it.
    """
    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Context {i}]\n"
            f"Source: {chunk['doc_name']}, Page {chunk['page_number']}\n"
            f"Relevance Score: {chunk['score']:.3f}\n"
            f"Content:\n{chunk['text']}\n"
        )

    return "\n" + "="*50 + "\n".join(context_parts)


# ── Chat Endpoint ────────────────────────────────────────────
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question about uploaded documents",
    description="Send a question and get a grounded answer with source citations",
)
async def chat(req: ChatRequest):
    """
    Answer a question using RAG (Retrieval Augmented Generation).

    Steps:
    1. Embed the question
    2. Find top-K relevant chunks from vector store
    3. Build a prompt with context + question
    4. Get GPT answer with citations
    5. Return answer + sources
    """

    # ── Step 1: Check we have documents ─────────────────────
    if store.index.ntotal == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded yet. Please upload a PDF first."
        )

    # ── Step 2: Embed the question ───────────────────────────
    try:
        query_vector = embed_one(req.question)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to embed question: {str(e)}"
        )

    # ── Step 3: Search for relevant chunks ──────────────────
    chunks = store.search(query_vector, k=settings.top_k)

    if not chunks:
        return ChatResponse(
            answer="I couldn't find any relevant information in the uploaded documents.",
            sources=[],
            chunks_found=0,
        )

    # ── Step 4: Build context for GPT ───────────────────────
    context = build_context(chunks)

    # ── Step 5: Build conversation messages ─────────────────
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # Add conversation history (last 6 messages for context)
    # We limit history to avoid exceeding token limits
    for msg in req.history[-6:]:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    # Add the current question with retrieved context
    messages.append({
        "role": "user",
        "content": (
            f"DOCUMENT CONTEXT:\n{context}\n\n"
            f"QUESTION: {req.question}\n\n"
            f"Please answer based only on the context above."
        ),
    })

    # ── Step 6: Call GPT ─────────────────────────────────────
    try:
        # REPLACE WITH THIS:
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=messages,
            temperature=0.1,
            max_completion_tokens=1000,    # ← FIXED!
        )
        answer = response.choices[0].message.content

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate answer: {str(e)}"
        )

    # ── Step 7: Format sources ───────────────────────────────
    sources = [
        SourceChunk(
            doc_name=chunk["doc_name"],
            page=chunk["page_number"],
            snippet=chunk["text"][:300],  # First 300 chars as preview
            score=round(chunk["score"], 4),
        )
        for chunk in chunks
    ]

    # ── Step 8: Return everything ────────────────────────────
    return ChatResponse(
        answer=answer,
        sources=sources,
        chunks_found=len(chunks),
    )
