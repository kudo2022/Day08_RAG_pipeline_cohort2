from __future__ import annotations

import math
from collections import Counter

from .rag_utils import metadata_matches, searchable_text, tokenize
from .task4_chunking_indexing import DEFAULT_DOMAIN, build_index


class SimpleBM25:
    def __init__(self, tokenized_corpus: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.tokenized_corpus = tokenized_corpus
        self.doc_len = [len(tokens) for tokens in tokenized_corpus]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0
        self.term_freqs = [Counter(tokens) for tokens in tokenized_corpus]

        self.doc_freqs: Counter[str] = Counter()
        for frequencies in self.term_freqs:
            for token in frequencies:
                self.doc_freqs[token] += 1

        total_docs = len(self.term_freqs)
        self.idf = {
            token: math.log(1 + (total_docs - freq + 0.5) / (freq + 0.5))
            for token, freq in self.doc_freqs.items()
        }

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0] * len(self.term_freqs)
        if not query_tokens or not self.term_freqs:
            return scores

        for token in query_tokens:
            token_idf = self.idf.get(token, 0.0)
            if token_idf == 0.0:
                continue

            for index, term_frequency in enumerate(self.term_freqs):
                tf = term_frequency.get(token, 0)
                if tf == 0:
                    continue

                doc_length = self.doc_len[index] or 1
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / max(self.avgdl, 1.0))
                scores[index] += token_idf * (tf * (self.k1 + 1)) / denominator

        return scores


def build_bm25_index(corpus: list[dict]) -> SimpleBM25:
    tokenized_corpus = [tokenize(searchable_text(doc)) for doc in corpus]
    return SimpleBM25(tokenized_corpus)


def _ensure_bm25(
    domain: str | None,
    allowed_types: set[str] | None,
) -> tuple[list[dict], SimpleBM25]:
    corpus = [
        {"content": chunk["content"], "metadata": dict(chunk["metadata"]), "embedding": list(chunk["embedding"])}
        for chunk in build_index()
        if metadata_matches(chunk, domain=domain, allowed_types=allowed_types)
    ]
    bm25 = build_bm25_index(corpus)
    return corpus, bm25


def lexical_search(
    query: str,
    top_k: int = 10,
    domain: str | None = DEFAULT_DOMAIN,
    allowed_types: set[str] | None = None,
) -> list[dict]:
    """Sparse retrieval using a small local BM25 implementation."""
    if top_k <= 0:
        return []

    corpus, bm25 = _ensure_bm25(domain=domain, allowed_types=allowed_types)
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
    results: list[dict] = []
    for index in ranked_indices[: max(top_k * 2, top_k)]:
        score = float(scores[index])
        if score <= 0:
            continue
        results.append(
            {
                "content": corpus[index]["content"],
                "score": score,
                "metadata": dict(corpus[index]["metadata"]),
                "embedding": list(corpus[index]["embedding"]),
            }
        )
        if len(results) >= top_k:
            break

    return results


if __name__ == "__main__":
    for result in lexical_search("Dieu 248 tang tru trai phep chat ma tuy", top_k=5):
        print(f"[{result['score']:.3f}] {result['metadata'].get('source')} -> {result['content'][:100]}...")
