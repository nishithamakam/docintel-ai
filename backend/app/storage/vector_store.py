"""
Vector Store - FAISS-based storage for embeddings + metadata.

What is FAISS?
- A library for fast similarity search on high-dimensional vectors
- Used by Meta, OpenAI, and many production RAG systems
- Free, open-source, runs on CPU (no GPU needed)

How does our store work?
- We store two things side-by-side:
    1. The FAISS index (just the math vectors)
    2. A Python list of metadata (chunk_id, doc_name, page, text)
- They're aligned by position: index[5] in FAISS ↔ metadata[5] in our list
- Both are saved to disk so the data survives restarts
"""
import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict
from app.config import DATA_DIR

# Where we save the index and metadata on disk
INDEX_PATH = DATA_DIR / "faiss_index" / "index.faiss"
META_PATH = DATA_DIR / "faiss_index" / "meta.pkl"

# Embedding dimension — must match the embedding model
# text-embedding-3-small → 1536 dimensions
EMBEDDING_DIM = 1536


class VectorStore:
    """
    A simple but production-grade vector store.

    Stores embeddings in FAISS for fast similarity search,
    and metadata in a parallel Python list for retrieval.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

        # If saved files exist on disk, load them. Otherwise, start fresh.
        if INDEX_PATH.exists() and META_PATH.exists():
            print(f"📂 Loading existing index from {INDEX_PATH}")
            self.index = faiss.read_index(str(INDEX_PATH))
            with open(META_PATH, "rb") as f:
                self.metadata: List[Dict] = pickle.load(f)
            print(f"   Loaded {len(self.metadata)} chunks")
        else:
            print(f"🆕 Creating new empty index (dim={dim})")
            # IndexFlatIP = brute-force inner product search
            # "Flat" = no approximation, exact results
            # "IP"   = inner product (≡ cosine similarity for normalized vectors)
            # Perfect for small-to-medium datasets (up to ~100K chunks)
            self.index = faiss.IndexFlatIP(dim)
            self.metadata: List[Dict] = []

    def add(self, vectors: np.ndarray, metas: List[Dict]) -> None:
        """
        Add new vectors and their metadata to the store.

        Args:
            vectors: NumPy array of shape (N, dim), dtype=float32
            metas:   List of N metadata dicts, one per vector
        """
        if len(vectors) != len(metas):
            raise ValueError(
                f"Mismatch: got {len(vectors)} vectors but {len(metas)} metadata entries"
            )

        if len(vectors) == 0:
            return  # nothing to add

        # Normalize vectors to unit length so inner product == cosine similarity
        # This modifies the array in-place
        vectors = vectors.astype("float32")  # ensure correct dtype
        faiss.normalize_L2(vectors)

        # Add to FAISS (this is the actual indexing step)
        self.index.add(vectors)

        # Append metadata in matching order
        self.metadata.extend(metas)

        # Save to disk so we don't lose data
        self._persist()

        print(f"   ✅ Added {len(metas)} chunks. Total chunks: {len(self.metadata)}")

    def search(self, query_vec: np.ndarray, k: int = 5) -> List[Dict]:
        """
        Find the top-k most similar chunks to a query vector.

        Args:
            query_vec: NumPy array of shape (1, dim) — a single query embedding
            k: Number of results to return

        Returns:
            List of metadata dicts, each augmented with a "score" field
            (cosine similarity, range -1 to +1, higher = more similar).
        """
        if self.index.ntotal == 0:
            # No data in the index yet
            return []

        # Same normalization as add() — required for IP == cosine
        query_vec = query_vec.astype("float32")
        faiss.normalize_L2(query_vec)

        # FAISS returns two arrays:
        #   scores: shape (1, k) — similarity scores
        #   idxs:   shape (1, k) — positions of the top-k vectors in the index
        scores, idxs = self.index.search(query_vec, k)

        results = []
        # We only sent 1 query, so we look at row 0
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                # FAISS returns -1 if there are fewer than k vectors total
                continue
            # Look up the matching metadata, attach the score, and return
            meta = dict(self.metadata[idx])  # copy, don't mutate
            meta["score"] = float(score)
            results.append(meta)

        return results

    def reset(self) -> None:
        """Wipe everything. Useful for testing."""
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata = []
        if INDEX_PATH.exists():
            INDEX_PATH.unlink()
        if META_PATH.exists():
            META_PATH.unlink()
        print("🗑️  Vector store reset")

    def _persist(self) -> None:
        """Save the index and metadata to disk."""
        faiss.write_index(self.index, str(INDEX_PATH))
        with open(META_PATH, "wb") as f:
            pickle.dump(self.metadata, f)


# Create a single store instance shared by the whole app
store = VectorStore()


# Quick test when running this file directly
if __name__ == "__main__":
    from app.ingestion.pdf_parser import parse_pdf
    from app.ingestion.chunker import chunk_pages
    from app.ingestion.embedder import embed_texts, embed_one
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.storage.vector_store <path-to-pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Reset for a clean test
    store.reset()

    # Step 1: Parse + chunk
    print(f"📄 Parsing {pdf_path}...")
    pages = parse_pdf(pdf_path)
    chunks = chunk_pages(pages, doc_id="test", doc_name=Path(pdf_path).name)
    print(f"✂️  Created {len(chunks)} chunks")

    # Step 2: Embed
    print(f"🤖 Embedding {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)
    print(f"   Got vectors of shape {vectors.shape}")

    # Step 3: Add to store
    print(f"💾 Adding to vector store...")
    store.add(vectors, chunks)

    # Step 4: Search!
    print("\n" + "=" * 60)
    print("🔍 Now let's test semantic search")
    print("=" * 60)

    test_queries = [
        "What should I do on Tuesday?",
        "How long is the longest run?",
        "Tell me about pace and effort levels",
    ]

    for query in test_queries:
        print(f"\n❓ Query: {query}")
        query_vec = embed_one(query)
        results = store.search(query_vec, k=3)

        for i, r in enumerate(results, 1):
            print(f"\n   #{i} — Page {r['page_number']}, score {r['score']:.4f}")
            print(f"      {r['text'][:200].strip()}...")
