from __future__ import annotations

import json
import numpy as np
from pathlib import Path
from typing import List, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# Optional imports
try:
    from sentence_transformers import SentenceTransformer
    _TRANSFORMERS = True
except ImportError:
    _TRANSFORMERS = False

class KnowledgeBase:
    """
    Unified Knowledge Base supporting TF-IDF and Embeddings.
    """

    def __init__(self, docs: List[dict], method: str = "tfidf", embedding_model: str = "all-MiniLM-L6-v2"):
        self.docs = docs
        self.method = method
        self.embeddings = None
        self.tfidf_matrix = None
        self.vectorizer = None
        self.model = None

        texts = [d['content'] for d in docs]

        if method == "embedding":
            if not _TRANSFORMERS:
                raise ImportError("Install sentence-transformers for embedding search.")
            self.model = SentenceTransformer(embedding_model)
            self.embeddings = self.model.encode(texts, normalize_embeddings=True)
        else:
            # TF-IDF Default
            self.vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)

    @classmethod
    def from_json(cls, path: Path, **kwargs):
        data = json.loads(Path(path).read_text())
        # Assume format [{"id": "1", "content": "..."}, ...]
        return cls(data, **kwargs)

    def search(self, query: str, top_k: int = 3) -> List[Tuple[dict, float]]:
        """Search documents. Returns list of (doc_dict, score)."""
        if self.method == "embedding":
            q_vec = self.model.encode([query], normalize_embeddings=True)
            scores = cosine_similarity(q_vec, self.embeddings)[0]
        else:
            q_vec = self.vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self.tfidf_matrix).flatten()

        # Get top k indices
        top_idx = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_idx:
            # Filter out zero scores
            if scores[idx] > 0.1: # Threshold
                results.append((self.docs[idx], float(scores[idx])))
        return results
