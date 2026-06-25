"""
Chat endpoint — uses the multi-agent orchestrator to answer questions.

Pipeline (handled by orchestrator):
    1. Retriever  → finds relevant chunks
    2. Analyst    → extracts key facts
    3. Reporter   → writes the final answer
    4. Critic     → verifies answer faithfulness

The endpoint itself is now thin — it just validates inputs,
delegates to the orchestrator, and shapes the response.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

from app.agents.orchestrator import run_pipeline

router = APIRouter()


# ── Request / Response models ────────────────────────────────
class Message(BaseModel):
    role: str        # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    question:  str
    history:   Optional[List[Message]] = []
    doc_ids:   Optional[List[str]]     = None    # filter to specific docs
    min_score: float                   = 0.25    # relevance threshold


class SourceChunk(BaseModel):
    doc_name: str
    page:     int
    location: str = ""
    snippet:  str
    score:    float


class AgentStep(BaseModel):
    agent:      str
    icon:       str
    summary:    str
    details:    Optional[str] = None
    duration_s: float


class TrustReport(BaseModel):
    faithful: bool
    score:    float
    issues:   List[str]
    verdict:  str


class ChatResponse(BaseModel):
    answer:       str
    sources:      List[SourceChunk]
    agent_steps:  List[AgentStep]
    trust:        TrustReport
    timings:      Dict[str, float]
    chunks_found: int


# ── Endpoint ──────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Run the multi-agent pipeline and return the structured result.
    """
    # Convert history to plain dicts for the orchestrator
    history_dicts = (
        [{"role": m.role, "content": m.content} for m in req.history]
        if req.history else []
    )

    # Call the orchestrator — does all the heavy lifting
    result = run_pipeline(
        question  = req.question,
        history   = history_dicts,
        doc_ids   = req.doc_ids,
        min_score = req.min_score,
        top_k     = 5,
    )

    # Shape into our response model
    return ChatResponse(
        answer       = result["answer"],
        sources      = [SourceChunk(**s) for s in result["sources"]],
        agent_steps  = [AgentStep(**s)   for s in result["agent_steps"]],
        trust        = TrustReport(**result["trust"]),
        timings      = result["timings"],
        chunks_found = result["chunks_found"],
    )
