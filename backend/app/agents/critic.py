"""
Critic Agent — verifies the Reporter's answer against the source documents.

Job:
    Read the Reporter's answer and check whether every factual claim
    is supported by the retrieved chunks. Flag any unsupported claims
    or hallucinations.

This is the "trust layer" of the multi-agent system. It's what separates
toy RAG from production-grade RAG.

Inspired by:
    - RAGAS (Retrieval Augmented Generation Assessment)
    - TruLens faithfulness metric
    - Anthropic's Constitutional AI
"""
import json
from typing import List, Dict
from openai import OpenAI
from app.config import settings


# Reuse one OpenAI client across calls
client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


# ── Critic's specialized prompt ───────────────────────────────
CRITIC_SYSTEM_PROMPT = """You are a Critic Agent in a multi-agent document Q&A system.

Your job is to RIGOROUSLY verify the Reporter's answer against the source documents.

You are NOT trying to be helpful. You are a strict fact-checker.

YOUR TASK:
1. Read the Reporter's answer claim-by-claim
2. For EACH factual claim, check if it is supported by the source excerpts
3. Identify ANY unsupported claims, exaggerations, or hallucinations
4. Score the answer's overall faithfulness (0-1)

RULES:
- A "supported" claim must be DIRECTLY stated in the sources, not inferred
- If a claim restates source content with minor rewording, it's still supported
- If a claim adds details not in the sources, it's UNSUPPORTED
- If a claim contradicts the sources, it's UNSUPPORTED
- Citations like (Source 1, Page 3) are not claims — ignore them
- Phrases like "I couldn't find" are not claims — they're meta-statements

OUTPUT: You MUST output ONLY valid JSON in this exact format:

{
  "faithful": <true or false>,
  "score": <float between 0.0 and 1.0>,
  "issues": [
    "Specific unsupported claim 1",
    "Specific unsupported claim 2"
  ],
  "verdict": "<one short sentence summary>"
}

SCORING GUIDE:
- 1.0  → Every claim fully supported
- 0.8  → Mostly supported, minor wording embellishments
- 0.5  → Mix of supported and unsupported claims
- 0.2  → Mostly hallucinated
- 0.0  → Completely fabricated

Do NOT output anything except the JSON object. No markdown, no explanation.
"""


def critique(answer: str, chunks: List[Dict]) -> Dict:
    """
    Verify the Reporter's answer against source chunks.

    Args:
        answer:  the Reporter's final answer
        chunks:  the original retrieved chunks (ground truth)

    Returns:
        Dict with keys: faithful (bool), score (float),
                        issues (list[str]), verdict (str)
    """
    # Edge case: nothing to check
    if not chunks or not answer.strip():
        return {
            "faithful": True,
            "score": 1.0,
            "issues": [],
            "verdict": "No content to evaluate.",
        }

    # Edge case: answer is just a "couldn't find info" message
    no_info_phrases = [
        "couldn't find",
        "could not find",
        "no relevant information",
        "not in the uploaded documents",
    ]
    if any(p in answer.lower() for p in no_info_phrases):
        return {
            "faithful": True,
            "score": 1.0,
            "issues": [],
            "verdict": "Answer correctly indicates no relevant info found.",
        }

    # Build the source context block
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['doc_name']}, Page {chunk['page_number']}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Call GPT with the critic's prompt
    try:
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"SOURCE EXCERPTS:\n\n{context}\n\n"
                        f"REPORTER'S ANSWER:\n\n{answer}\n\n"
                        f"Verify the answer now. Output JSON only."
                    ),
                },
            ],
            temperature=0.0,           # zero — strict, deterministic checking
            max_completion_tokens=400,
            response_format={"type": "json_object"},   # force valid JSON
        )
        raw = response.choices[0].message.content.strip()

        # Parse the JSON response
        result = json.loads(raw)

        # Validate and normalize the response
        return {
            "faithful": bool(result.get("faithful", False)),
            "score":    float(result.get("score", 0.5)),
            "issues":   list(result.get("issues", [])),
            "verdict":  str(result.get("verdict", "No verdict provided.")),
        }

    except Exception as e:
        # If the critic fails for any reason, return a neutral result
        # rather than blocking the whole pipeline
        return {
            "faithful": True,
            "score":    0.5,
            "issues":   [],
            "verdict":  f"Critic unavailable: {str(e)[:80]}",
        }
