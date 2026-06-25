"""
Reporter Agent — writes the final answer for the user.
"""
from typing import List, Dict
from openai import OpenAI
from app.config import settings

client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

REPORTER_SYSTEM_PROMPT = """You are a Reporter Agent in a multi-agent document Q&A system.

Your job is to write a clear, helpful answer to the user's question using
ONLY the facts provided to you by the Analyst Agent.

RULES:
1. Use ONLY the facts provided. Do NOT add outside knowledge.
2. Write in natural, professional prose — not bullet points (unless the
   answer is genuinely a list).
3. Keep inline citations like (Source 1, Page 3) directly after each claim.
4. Be concise: aim for 2-5 sentences unless the question demands more.
5. If the facts are "NO_RELEVANT_FACTS", politely say:
   "I couldn't find relevant information in the uploaded documents."
6. Do NOT invent details. If a fact is not stated, do not state it.
7. Use markdown formatting (bold, bullets) only when it improves clarity.

TONE:
- Professional but friendly
- Confident but precise
- Like a helpful enterprise assistant
"""


def report(question: str, facts: str, chunks: List[Dict]) -> str:
    """Generate the final answer from extracted facts."""
    # No-info case: skip the GPT call
    if not facts or facts.strip() == "NO_RELEVANT_FACTS" or not chunks:
        return (
            "I couldn't find relevant information in the uploaded documents "
            "to answer this question. Try rephrasing, or upload a document "
            "that covers this topic."
        )

    # Build raw context as a safety net for the model
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['doc_name']}, Page {chunk['page_number']}]\n"
            f"{chunk['text']}"
        )
    raw_context = "\n\n---\n\n".join(context_parts)

    # Call the model
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": REPORTER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"USER'S QUESTION:\n{question}\n\n"
                    f"FACTS EXTRACTED BY ANALYST:\n{facts}\n\n"
                    f"ORIGINAL DOCUMENT EXCERPTS (for reference):\n{raw_context}\n\n"
                    f"Write the final answer now."
                ),
            },
        ],
        temperature=0.3,
        max_completion_tokens=2500,
    )

    # ── Guard against empty/None content ──────────────────────
    content = response.choices[0].message.content
    if not content:
        return (
            "I couldn't generate a response for this question. "
            "Please try rephrasing it."
        )
    return content.strip()
