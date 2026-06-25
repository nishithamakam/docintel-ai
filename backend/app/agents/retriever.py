"""
Retriever Agent — finds relevant document chunks for a question.

Job:
    Given a question, return the top-k most semantically similar
    chunks from the FAISS vector store.

This is the "search brain" of the system.
"""
from typing import List, Dict, Optional
from app.ingestion.embedder import embed_texts
from app.storage.vector_store import store


def retrieve(
    question: str,
    k: int = 5,
    doc_ids: Optional[List[str]] = None,
    min_score: float = 0.25,
) -> List[Dict]:
    """
    Retrieve relevant chunks for a question.

    Args:
        question:   the user's question
        k:          number of chunks to return
        doc_ids:    optional list of doc IDs to restrict search to
        min_score:  minimum cosine similarity threshold

    Returns:
        List of chunk dicts, each with: doc_id, doc_name,
        page_number, text, score
    """
    # Step 1: Embed the question into a vector
    query_vector = embed_texts([question])

    # Step 2: Search FAISS for similar chunks
    chunks = store.search(
        query_vector,
        k=k,
        doc_ids=doc_ids,
        min_score=min_score,
    )

    return chunks
