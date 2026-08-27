import math
import re
from typing import List, Dict, Any, Optional
import numpy as np

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from app.config import OPENAI_API_KEY


class CodeVectorStore:
    """
    Hybrid Search Vector & Lexical Store for codebases.
    Uses Reciprocal Rank Fusion (RRF) between Dense Semantic Vectors and BM25 / Keyword Retrieval.
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
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY) if (OPENAI_API_KEY and OpenAI) else None

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenizes code text into identifiers, split camelCase, snake_case, and symbols."""
        tokens = []
        # Split by non-alphanumeric
        raw_words = re.findall(r"[a-zA-Z0-9_]+", text)
        for w in raw_words:
            tokens.append(w.lower())
            # Split camelCase
            camel_split = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)", w)
            if len(camel_split) > 1:
                for sub in camel_split:
                    tokens.append(sub.lower())
        return tokens

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        """Indexes all code chunks into BM25 and vector stores."""
        self.chunks = chunks
        num_docs = len(chunks)
        if num_docs == 0:
            return

        # 1. Build Lexical BM25 Index
        self.doc_term_freqs = []
        self.doc_lengths = []
        doc_freqs: Dict[str, int] = {}

        for chunk in chunks:
            # Weighted search text: include file path and symbol multiple times to boost relevance
            searchable_text = f"{chunk['file_path']} {chunk['file_path']} {chunk.get('symbol', '')} {chunk.get('symbol', '')}\n{chunk['content']}"
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

        # 2. Build Dense Embeddings (OpenAI if available, else TF-IDF Sparse Embeddings)
        if self.openai_client:
            try:
                texts = [
                    f"File: {c['file_path']}\nSymbol: {c.get('symbol', '')}\n{c['content'][:1500]}"
                    for c in chunks
                ]
                # Batch in groups of 100
                all_embs = []
                for i in range(0, len(texts), 100):
                    batch = texts[i : i + 100]
                    res = self.openai_client.embeddings.create(
                        input=batch,
                        model="text-embedding-3-small"
                    )
                    all_embs.extend([item.embedding for item in res.data])
                self.chunk_embeddings = np.array(all_embs, dtype=np.float32)
                # Normalize
                norms = np.linalg.norm(self.chunk_embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                self.chunk_embeddings = self.chunk_embeddings / norms
            except Exception as e:
                # Fallback to sparse vector
                self._build_sparse_embeddings(chunks)
        else:
            self._build_sparse_embeddings(chunks)

    def _build_sparse_embeddings(self, chunks: List[Dict[str, Any]]):
        """Zero-dependency TF-IDF feature matrix vectorizer."""
        top_terms = sorted(self.idf.items(), key=lambda x: x[1], reverse=True)[:2000]
        self.vocab = {term: idx for idx, (term, _) in enumerate(top_terms)}
        dim = len(self.vocab)

        matrix = np.zeros((len(chunks), max(1, dim)), dtype=np.float32)
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
        """Dense cosine similarity search."""
        if self.chunk_embeddings is None or len(self.chunks) == 0:
            return []

        query_vec = None
        if self.openai_client:
            try:
                res = self.openai_client.embeddings.create(
                    input=[query],
                    model="text-embedding-3-small"
                )
                query_vec = np.array(res.data[0].embedding, dtype=np.float32)
                q_norm = np.linalg.norm(query_vec)
                if q_norm > 0:
                    query_vec = query_vec / q_norm
            except Exception:
                query_vec = None

        if query_vec is None:
            # Sparse fallback
            dim = max(1, len(self.vocab))
            query_vec = np.zeros(dim, dtype=np.float32)
            for t in self.tokenize(query):
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
        if not self.chunks:
            return []

        bm25_results = self._bm25_search(query, top_k=20)
        dense_results = self._dense_search(query, top_k=20)

        # RRF formula: RRF_score = 1 / (60 + rank)
        rrf_scores: Dict[int, float] = {}

        for rank, (doc_idx, _) in enumerate(bm25_results):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (60.0 + rank + 1.0))

        for rank, (doc_idx, _) in enumerate(dense_results):
            rrf_scores[doc_idx] = rrf_scores.get(doc_idx, 0.0) + (1.0 / (60.0 + rank + 1.0))

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for doc_idx, score in sorted_docs:
            chunk = self.chunks[doc_idx]
            results.append({
                **chunk,
                "relevance_score": round(score, 4),
            })

        return results


# In-memory registry of active repo vector stores
VECTOR_STORES: Dict[str, CodeVectorStore] = {}


def get_or_create_vector_store(repo_id: str) -> CodeVectorStore:
    if repo_id not in VECTOR_STORES:
        VECTOR_STORES[repo_id] = CodeVectorStore(repo_id)
    return VECTOR_STORES[repo_id]
