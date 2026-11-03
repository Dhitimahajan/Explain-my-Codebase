import math
import re
from typing import List, Dict, Any, Optional
import numpy as np


class CodeVectorStore:
    """
    High-Performance Hybrid Search Vector & Lexical Store for codebases.
    Uses Reciprocal Rank Fusion (RRF) between TF-IDF Subword Vectors and BM25 Keyword Retrieval.
    Runs 100% locally with sub-millisecond search and zero network latency.
    """

    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self.chunks: List[Dict[str, Any]] = []
        self.chunk_embeddings: Optional[np.ndarray] = None
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Fast tokenizer for code identifiers, camelCase, and snake_case."""
        tokens = []
        raw_words = re.findall(r"[a-zA-Z0-9_]+", text)
        for w in raw_words:
            tokens.append(w.lower())
            camel_split = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)", w)
            if len(camel_split) > 1:
                for sub in camel_split:
                    tokens.append(sub.lower())
        return tokens

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        """Indexes code chunks in sub-second time using sparse vector representation."""
        self.chunks = chunks
        num_docs = len(chunks)
        if num_docs == 0:
            return

        # 1. Build Lexical BM25 Index
        self.doc_term_freqs = []
        self.doc_lengths = []
        doc_freqs: Dict[str, int] = {}

        for chunk in chunks:
            searchable_text = f"{chunk['file_path']} {chunk['file_path']} {chunk.get('symbol', '')}\n{chunk['content'][:2000]}"
            tokens = self.tokenize(searchable_text)
            self.doc_lengths.append(len(tokens))

            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs.append(tf)

            for t in tf.keys():
                doc_freqs[t] = doc_freqs.get(t, 0) + 1

        self.avg_doc_length = sum(self.doc_lengths) / max(1, num_docs)

        # Compute IDF
        self.idf = {}
        for term, df in doc_freqs.items():
            self.idf[term] = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)

        # 2. Build Sparse Feature Matrix
        top_terms = sorted(self.idf.items(), key=lambda x: x[1], reverse=True)[:1500]
        self.vocab = {term: idx for idx, (term, _) in enumerate(top_terms)}
        dim = max(1, len(self.vocab))

        matrix = np.zeros((len(chunks), dim), dtype=np.float32)
        for i, tf in enumerate(self.doc_term_freqs):
            for term, count in tf.items():
                if term in self.vocab:
                    col = self.vocab[term]
                    matrix[i, col] = count * self.idf.get(term, 1.0)

        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.chunk_embeddings = matrix / norms

    def _bm25_search(self, query: str, top_k: int = 15) -> List[tuple]:
        """Calculates BM25 scores for query."""
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores = []
        k1 = 1.5
        b = 0.75

        for idx, (tf, doc_len) in enumerate(zip(self.doc_term_freqs, self.doc_lengths)):
            score = 0.0
            for qt in query_tokens:
                if qt in tf:
                    term_freq = tf[qt]
                    idf_val = self.idf.get(qt, 0.0)
                    numerator = term_freq * (k1 + 1)
                    denominator = term_freq + k1 * (1 - b + b * (doc_len / max(1.0, self.avg_doc_length)))
                    score += idf_val * (numerator / max(0.001, denominator))
            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _dense_search(self, query: str, top_k: int = 15) -> List[tuple]:
        """Fast cosine similarity search on normalized sparse vectors."""
        if self.chunk_embeddings is None or len(self.chunks) == 0:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        dim = max(1, len(self.vocab))
        query_vec = np.zeros(dim, dtype=np.float32)
        for t in query_tokens:
            if t in self.vocab:
                query_vec[self.vocab[t]] += self.idf.get(t, 1.0)
        
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        similarities = np.dot(self.chunk_embeddings, query_vec)
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(int(idx), float(similarities[idx])) for idx in top_indices if similarities[idx] > 0]

    def search(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """
        Performs hybrid retrieval using Reciprocal Rank Fusion (RRF).
        """
        if not self.chunks or not query or not query.strip():
            return []

        safe_top_k = max(1, top_k)
        bm25_results = self._bm25_search(query, top_k=safe_top_k * 2)
        dense_results = self._dense_search(query, top_k=safe_top_k * 2)

        rrf_scores: Dict[int, float] = {}

        for rank, (doc_idx, _) in enumerate(bm25_results):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (60.0 + rank + 1.0))

        for rank, (doc_idx, _) in enumerate(dense_results):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (60.0 + rank + 1.0))

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:safe_top_k]

        results = []
        for doc_idx, score in sorted_docs:
            chunk = self.chunks[doc_idx]
            results.append({
                **chunk,
                "relevance_score": round(score, 4),
            })

        return results


# In-memory registry of active repo vector stores with bounded size for serverless
VECTOR_STORES: Dict[str, CodeVectorStore] = {}
MAX_CACHED_STORES = 25


def get_or_create_vector_store(repo_id: str) -> CodeVectorStore:
    global VECTOR_STORES
    if repo_id not in VECTOR_STORES:
        if len(VECTOR_STORES) >= MAX_CACHED_STORES:
            # Pop oldest entry to prevent memory exhaustion in serverless containers
            oldest_key = next(iter(VECTOR_STORES))
            del VECTOR_STORES[oldest_key]
        VECTOR_STORES[repo_id] = CodeVectorStore(repo_id)
    return VECTOR_STORES[repo_id]
