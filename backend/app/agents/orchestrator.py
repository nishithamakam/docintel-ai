"""
Orchestrator — runs the multi-agent pipeline.
1. Retriever → 2. Analyst → 3. Reporter → 4. Critic
"""
import time
from typing import List, Dict, Optional

from app.agents.retriever import retrieve
from app.agents.analyst   import analyze
from app.agents.reporter  import report
from app.agents.critic    import critique


def run_pipeline(
    question: str,
    history: Optional[List[Dict]] = None,
    doc_ids: Optional[List[str]] = None,
    min_score: float = 0.25,
    top_k: int = 5,
) -> Dict:
    timings = {}
    agent_steps = []

    # STEP 1: RETRIEVER
    t0 = time.time()
    chunks = retrieve(question=question, k=top_k, doc_ids=doc_ids, min_score=min_score)
    timings["retriever"] = round(time.time() - t0, 2)
    agent_steps.append({
        "agent": "Retriever",
        "icon": "search",
        "summary": f"Found {len(chunks)} relevant chunk(s)",
        "duration_s": timings["retriever"],
    })

    if not chunks:
        return {
            "answer": (
                "I couldn't find relevant information in the selected "
                "documents. Try rephrasing, or make sure the right "
                "documents are selected."
            ),
            "sources": [],
            "agent_steps": agent_steps,
            "trust": {"faithful": True, "score": 1.0, "issues": [], "verdict": "No relevant chunks retrieved."},
            "timings": timings,
            "chunks_found": 0,
        }

    # STEP 2: ANALYST
    t0 = time.time()
    facts = analyze(question=question, chunks=chunks) or "NO_RELEVANT_FACTS"
    timings["analyst"] = round(time.time() - t0, 2)
    fact_count = len([l for l in facts.split("\n") if l.strip().startswith("-")])
    agent_steps.append({
        "agent": "Analyst",
        "icon": "list",
        "summary": f"Extracted {fact_count} key fact(s)",
        "details": facts,
        "duration_s": timings["analyst"],
    })

    # STEP 3: REPORTER
    t0 = time.time()
    answer = report(question=question, facts=facts, chunks=chunks) or "I generated an empty response. Please rephrase your question."
    timings["reporter"] = round(time.time() - t0, 2)
    agent_steps.append({
        "agent": "Reporter",
        "icon": "pen",
        "summary": f"Generated answer ({len(answer or '')} chars)",
        "duration_s": timings["reporter"],
    })

    # STEP 4: CRITIC
    t0 = time.time()
    trust = critique(answer=answer, chunks=chunks)
    timings["critic"] = round(time.time() - t0, 2)
    agent_steps.append({
        "agent": "Critic",
        "icon": "shield",
        "summary": trust.get("verdict", "Reviewed answer"),
        "details": f"Faithfulness score: {trust.get('score', 0):.2f}",
        "duration_s": timings["critic"],
    })

    sources = [
        {
            "doc_name": c["doc_name"],
            "page": c["page_number"],
            "location": f"{c.get('section_kind', 'page').capitalize()} {c['page_number']}",
            "snippet": c["text"][:300],
            "score": round(c["score"], 4),
        }
        for c in chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
        "agent_steps": agent_steps,
        "trust": trust,
        "timings": timings,
        "chunks_found": len(chunks),
    }
