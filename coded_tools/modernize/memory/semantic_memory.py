# Copyright © 2025-2026 Cognizant Technology Solutions Corp, www.cognizant.com.
"""
Tier 3: Semantic Memory Engine.
Provides an on-premise, in-house vector and BM25 hybrid semantic search engine.
No external vector databases required.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class DocumentChunk:
    """Represents a text chunk in Semantic Memory with strict provenance."""

    def __init__(
        self,
        chunk_id: str,
        content: str,
        source_file: str,
        start_line: int,
        end_line: int,
        chunk_type: str = "doc",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.chunk_id: str = chunk_id
        self.content: str = content
        self.source_file: str = source_file.replace("\\", "/")
        self.start_line: int = start_line
        self.end_line: int = end_line
        self.chunk_type: str = chunk_type
        self.metadata: Dict[str, Any] = metadata or {}
        self.tokens: List[str] = self._tokenize(content)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r"[A-Za-z0-9_]+", text.lower())
        return words

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "source_file": self.source_file,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "chunk_type": self.chunk_type,
            "metadata": self.metadata,
        }


class SemanticMemory:
    """
    Tier 3 Semantic Memory implementing BM25 + Vector Cosine Hybrid Search locally.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.chunks: List[DocumentChunk] = []
        self.chunk_map: Dict[str, DocumentChunk] = {}
        self.k1 = k1
        self.b = b
        self.doc_len: List[int] = []
        self.avg_doc_len: float = 0.0
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.term_freqs: List[Dict[str, int]] = []
        self._fitted = False

    def add_chunk(
        self,
        content: str,
        source_file: str,
        start_line: int,
        end_line: int,
        chunk_type: str = "doc",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentChunk:
        chunk_id = f"chunk_{len(self.chunks) + 1}_{re.sub(r'[^a-zA-Z0-9]', '_', source_file)}"
        chunk = DocumentChunk(chunk_id, content, source_file, start_line, end_line, chunk_type, metadata)
        self.chunks.append(chunk)
        self.chunk_map[chunk_id] = chunk
        self._fitted = False
        return chunk

    def build_index(self):
        """Builds local vocabulary, term frequency, and IDF indices."""
        n = len(self.chunks)
        if n == 0:
            return

        self.doc_len = [len(c.tokens) for c in self.chunks]
        self.avg_doc_len = sum(self.doc_len) / max(1, n)

        df: Dict[str, int] = {}
        self.term_freqs = []

        for chunk in self.chunks:
            tf: Dict[str, int] = {}
            for t in chunk.tokens:
                tf[t] = tf.get(t, 0) + 1
            self.term_freqs.append(tf)
            for t in tf.keys():
                df[t] = df.get(t, 0) + 1

        # Calculate BM25 IDF
        self.idf = {}
        for term, freq in df.items():
            # BM25 standard IDF with smoothing
            self.idf[term] = math.log((n - freq + 0.5) / (freq + 0.5) + 1.0)

        # Build vocabulary vector space
        self.vocab = {term: idx for idx, term in enumerate(df.keys())}
        self._fitted = True

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Runs hybrid BM25 + term-vector cosine similarity on the in-house index.
        """
        if not self._fitted:
            self.build_index()

        n = len(self.chunks)
        if n == 0:
            return []

        query_tokens = DocumentChunk._tokenize(query)
        if not query_tokens:
            return []

        # 1. BM25 Scores
        bm25_scores = np.zeros(n)
        for i, tf in enumerate(self.term_freqs):
            score = 0.0
            doc_l = self.doc_len[i]
            for qt in query_tokens:
                if qt in tf:
                    f = tf[qt]
                    denom = f + self.k1 * (1.0 - self.b + self.b * (doc_l / max(1e-5, self.avg_doc_len)))
                    score += self.idf.get(qt, 0.0) * (f * (self.k1 + 1.0)) / max(1e-5, denom)
            bm25_scores[i] = score

        # Normalize BM25
        max_bm25 = np.max(bm25_scores) if np.max(bm25_scores) > 0 else 1.0
        norm_bm25 = bm25_scores / max_bm25

        # 2. Dense Cosine Similarity (TF-IDF vector representation)
        q_vec = np.zeros(len(self.vocab))
        for qt in query_tokens:
            if qt in self.vocab:
                q_vec[self.vocab[qt]] += self.idf.get(qt, 1.0)
        q_norm = np.linalg.norm(q_vec)

        cosine_scores = np.zeros(n)
        if q_norm > 0:
            for i, tf in enumerate(self.term_freqs):
                d_vec = np.zeros(len(self.vocab))
                for t, count in tf.items():
                    if t in self.vocab:
                        d_vec[self.vocab[t]] = count * self.idf.get(t, 1.0)
                d_norm = np.linalg.norm(d_vec)
                if d_norm > 0:
                    cosine_scores[i] = np.dot(q_vec, d_vec) / (q_norm * d_norm)

        # 3. Hybrid Combined Score (60% BM25 + 40% Vector Cosine)
        hybrid_scores = 0.6 * norm_bm25 + 0.4 * cosine_scores

        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(hybrid_scores[idx])
            if score > 0.01:
                chunk = self.chunks[idx]
                results.append({
                    "chunk_id": chunk.chunk_id,
                    "score": round(score, 4),
                    "bm25_score": round(float(norm_bm25[idx]), 4),
                    "cosine_score": round(float(cosine_scores[idx]), 4),
                    "content": chunk.content,
                    "source_file": chunk.source_file,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    "metadata": chunk.metadata,
                })

        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_chunks": len(self.chunks),
            "chunks": [c.to_dict() for c in self.chunks],
        }
