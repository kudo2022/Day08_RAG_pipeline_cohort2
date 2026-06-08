from __future__ import annotations

from .rag_utils import cosine_similarity, hash_embedding, tokenize
from .task4_chunking_indexing import EMBEDDING_DIM, build_index


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Dense retrieval using the local hash embeddings from Task 4."""
    if top_k <= 0:
        return []

    query_tokens = set(tokenize(query))
    query_embedding = hash_embedding(query, EMBEDDING_DIM)
    results: list[dict] = []

    for chunk in build_index():
        semantic_score = cosine_similarity(query_embedding, chunk["embedding"])
        chunk_tokens = set(tokenize(chunk["content"]))
        overlap_score = len(query_tokens & chunk_tokens) / max(len(query_tokens), 1) if query_tokens else 0.0
        score = 0.8 * semantic_score + 0.2 * overlap_score
        if score <= 0:
            continue

        results.append(
            {
                "content": chunk["content"],
                "score": float(score),
                "metadata": dict(chunk["metadata"]),
                "embedding": list(chunk["embedding"]),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    for result in semantic_search("hinh phat cho toi tang tru ma tuy", top_k=5):
        print(f"[{result['score']:.3f}] {result['metadata'].get('source')} -> {result['content'][:100]}...")
