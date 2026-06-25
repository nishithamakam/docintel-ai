"""
Analyst Agent — extracts key facts from retrieved chunks.

Job:
    Given a question + retrieved chunks, extract a structured list
    of relevant facts. The reporter agent uses these facts to
    write the final answer.

Why this matters:
    Without this step, the LLM has to do "understand context AND write
    answer" in one pass. By separating them, each step is more reliable
    and the reasoning is more transparent.
"""
from typing import List, Dict
from openai import OpenAI
from app.config import settings


# Reuse one OpenAI client across calls
client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


# ── Analyst's specialized prompt ──────────────────────────────
ANALYST_SYSTEM_PROMPT = """You are an Analyst Agent in a multi-agent document Q&A system.

Your ONLY job is to extract key facts from document excerpts that are relevant
to a user's question. You do NOT write the final answer — that's the Reporter's job.

RULES:
1. Read each excerpt carefully.
2. Extract 3-7 specific, factual statements that help answer the question.
3. Each fact must include a source citation: (Source N, Page X)
4. ONLY use information explicitly stated in the excerpts.
5. If an excerpt is irrelevant, skip it.
6. If NO excerpts contain relevant info, output: "NO_RELEVANT_FACTS"

OUTPUT FORMAT:
- Plain bulleted list, one fact per line
- Each fact ≤ 25 words
- Always include citation in parentheses

Example output:
- The longest training run is 18 km. (Source 1, Page 1)
- Recovery weeks reduce long run distance by 30%. (Source 2, Page 5)
- Tuesday workouts focus on intervals at 10K pace. (Source 1, Page 3)
"""


def analyze(question: str, chunks: List[Dict]) -> str:
    """
    Extract relevant facts from chunks.

    Args:
        question: the user's question
        chunks:   list of retrieved chunks (from Retriever)

    Returns:
        A bullet-point list of facts as a single string.
        If nothing relevant: "NO_RELEVANT_FACTS"
    """
    if not chunks:
        return "NO_RELEVANT_FACTS"

    # Build a numbered context block for the analyst
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['doc_name']}, Page {chunk['page_number']}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Call GPT with the analyst's specialized prompt
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"USER'S QUESTION: {question}\n\n"
                    f"DOCUMENT EXCERPTS:\n\n{context}\n\n"
                    f"Extract the key facts now."
                ),
            },
        ],
        temperature=0.1,           # very low — we want consistent extraction
        max_completion_tokens=500,
    )

    return response.choices[0].message.content.strip()
