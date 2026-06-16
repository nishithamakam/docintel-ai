"""
Embedder - Converts text into vector embeddings using the BMS gateway.

What is an embedding?
- A list of numbers (e.g., 1536 floats) that represents the meaning of text.
- Texts with similar meanings have similar embedding vectors.
- This is the "magic" that lets RAG find relevant chunks even when the
  user's question uses different words from the document.

Why batch?
- The OpenAI API supports embedding many texts in a single call.
- Much faster and cheaper than one-at-a-time.
- We batch in groups of 100 to stay safely under API limits.
"""
from openai import OpenAI
from typing import List
import numpy as np
from app.config import settings

# Create one client at module load (reused for all calls)
client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

# OpenAI's embedding API allows up to 2048 inputs per request,
# but we keep it conservative to avoid timeouts on slow networks.
BATCH_SIZE = 100


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Convert a list of text strings into embedding vectors.

    Args:
        texts: List of strings to embed (e.g., chunk texts)

    Returns:
        A NumPy array of shape (N, D) where:
        - N = number of input texts
        - D = embedding dimension (1536 for text-embedding-3-small)
        - dtype is float32 (compact, GPU-friendly, what FAISS expects)

    Example:
        vectors = embed_texts(["hello", "world"])
        # vectors.shape == (2, 1536)
    """
    if not texts:
        # Edge case: no input → return empty array with correct shape
        return np.zeros((0, 1536), dtype="float32")

    all_embeddings = []

    # Process in batches to stay under API limits
    for batch_start in range(0, len(texts), BATCH_SIZE):
        batch = texts[batch_start : batch_start + BATCH_SIZE]

        # Call the BMS gateway
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )

        # response.data is a list of embedding objects, one per input text
        # Each has a `.embedding` attribute which is a list of floats
        for item in response.data:
            all_embeddings.append(item.embedding)

    # Convert Python list-of-lists to a NumPy 2D array
    # float32 is the standard for vector databases (smaller, faster than float64)
    return np.array(all_embeddings, dtype="float32")


def embed_one(text: str) -> np.ndarray:
    """
    Convenience function for embedding a single text (e.g., a user query).

    Args:
        text: A single string to embed

    Returns:
        A NumPy array of shape (1, D) — kept 2D so it works directly with
        FAISS search functions which expect a batch of queries.
    """
    return embed_texts([text])


# Quick test when running this file directly
if __name__ == "__main__":
    print(f"🤖 Using embedding model: {settings.embedding_model}")
    print(f"🌐 Connecting to: {settings.openai_base_url}\n")

    # Test with three sentences of varying similarity
    test_texts = [
        "How do I get a refund?",
        "What is the return policy?",
        "How do I cook spaghetti?",
    ]

    print("📤 Embedding 3 test sentences...\n")
    vectors = embed_texts(test_texts)

    print(f"✅ Got embeddings of shape: {vectors.shape}")
    print(f"   ({vectors.shape[0]} texts, each with {vectors.shape[1]} dimensions)\n")

    # Compute similarity between sentences using cosine similarity
    # Cosine similarity = dot product of normalized vectors
    # Range: -1 (opposite) to +1 (identical), with 0 = unrelated
    print("🔍 Cosine similarity between sentences:")
    print("   (closer to 1.0 = more similar in meaning)\n")

    # Normalize all vectors to unit length
    normalized = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    pairs = [
        (0, 1, "refund vs return"),
        (0, 2, "refund vs cooking"),
        (1, 2, "return vs cooking"),
    ]
    for i, j, label in pairs:
        similarity = float(np.dot(normalized[i], normalized[j]))
        print(f"   {label:25s} → {similarity:.4f}")
