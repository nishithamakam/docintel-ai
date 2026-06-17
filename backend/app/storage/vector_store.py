"""
Vector Store — FAISS-based storage and retrieval.
Stores normalized embeddings + metadata, persists to disk.
"""
import os
import pickle
import faiss
import numpy as np
from typing import List, Dict, Optional

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR  = os.path.join(BASE_DIR, "..", "..", "data", "faiss_index")
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
META_PATH  = os.path.join(INDEX_DIR, "meta.pkl")

os.makedirs(INDEX_DIR, exist_ok=True)

# ── Dimension of text-embedding-3-small ──────────────────────────────────────
EMBEDDING_DIM = 1536


class VectorStore:
    """
    Wraps a FAISS flat index with aligned metadata.
    Supports add, search (with optional doc_id filter + score threshold),
    and disk persistence.
    """

    def __init__(self):
        if os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
            print(f"📂 Loading existing index from {INDEX_PATH}")
            self.index    = faiss.read_index(INDEX_PATH)
            with open(META_PATH, "rb") as f:
                self.metadata = pickle.load(f)
            print(f"   Loaded {len(self.metadata)} chunks")
        else:
            print("🆕 Creating new FAISS index")
            self.index    = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.metadata: List[Dict] = []

    # ── Add ──────────────────────────────────────────────────────────────────
    def add(self, embeddings: np.ndarray, metadata: List[Dict]) -> None:
        """
        Add embeddings + aligned metadata to the store.

        Args:
            embeddings: float32 array of shape (n, EMBEDDING_DIM)
            metadata:   list of n dicts (one per chunk)
        """
        if len(embeddings) == 0:
            return

        vecs = embeddings.astype("float32")
        faiss.normalize_L2(vecs)

        self.index.add(vecs)
        self.metadata.extend(metadata)
        self._save()
        print(f"   ✅ Added {len(embeddings)} chunks. Total chunks: {len(self.metadata)}")

    # ── Search ───────────────────────────────────────────────────────────────
    def search(
        self,
        query_vec: np.ndarray,
        k: int = 5,
        doc_ids: Optional[List[str]] = None,
        min_score: float = 0.0,
    ) -> List[Dict]:
        """
        Find the top-k most similar chunks to a query vector.

        Args:
            query_vec:  float32 array of shape (1, EMBEDDING_DIM)
            k:          number of results to return (after filtering)
            doc_ids:    optional list of doc IDs to restrict search to;
                        if None, searches across all documents
            min_score:  minimum cosine similarity score (0-1);
                        chunks below this threshold are dropped

        Returns:
            List of metadata dicts with an added 'score' field,
            sorted by descending relevance.
        """
        if self.index.ntotal == 0:
            return []

        query_vec = query_vec.astype("float32")
        faiss.normalize_L2(query_vec)

        # Over-fetch so filters don't leave us short
        fetch_k = min(k * 5 if doc_ids else k, self.index.ntotal)
        scores, idxs = self.index.search(query_vec, fetch_k)

        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue

            meta = dict(self.metadata[idx])
            meta["score"] = float(score)

            # Filter 1: restrict to selected docs
            if doc_ids and meta.get("doc_id") not in doc_ids:
                continue

            # Filter 2: drop weak matches
            if meta["score"] < min_score:
                continue

            results.append(meta)

            if len(results) >= k:
                break

        return results

    # ── Persist ──────────────────────────────────────────────────────────────
    def _save(self) -> None:
        """Write index and metadata to disk."""
        faiss.write_index(self.index, INDEX_PATH)
        with open(META_PATH, "wb") as f:
            pickle.dump(self.metadata, f)


# Singleton — imported everywhere
store = VectorStore()
