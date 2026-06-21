from __future__ import annotations

from .task5_semantic_search import semantic_search
from .task6_lexical_search import lexical_search
from .task7_reranking import rerank, rerank_rrf
from .task8_pageindex_vectorless import pageindex_search
from .task4_chunking_indexing import DEFAULT_DOMAIN

SCORE_THRESHOLD = 0.3
DEFAULT_TOP_K = 5
RERANK_METHOD = "cross_encoder"


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
    domain: str | None = DEFAULT_DOMAIN,
    allowed_types: set[str] | None = None,
) -> list[dict]:
    """Run hybrid retrieval with PageIndex fallback."""
    if top_k <= 0:
        return []

    dense_results = semantic_search(
        query,
        top_k=max(top_k * 2, 6),
        domain=domain,
        allowed_types=allowed_types,
    )
    sparse_results = lexical_search(
        query,
        top_k=max(top_k * 2, 6),
        domain=domain,
        allowed_types=allowed_types,
    )
    merged_results = rerank_rrf([dense_results, sparse_results], top_k=max(top_k * 2, 6))

    for item in merged_results:
        item["source"] = "hybrid"

    if use_reranking and merged_results:
        final_results = rerank(query, merged_results, top_k=top_k, method=RERANK_METHOD)
    else:
        final_results = merged_results[:top_k]

    for item in final_results:
        item["source"] = "hybrid"

    best_score = final_results[0]["score"] if final_results else 0.0
    if not final_results or best_score < score_threshold:
        fallback_results = pageindex_search(
            query,
            top_k=top_k,
            domain=domain,
            allowed_types=allowed_types,
        )
        if fallback_results:
            return fallback_results[:top_k]

    return final_results[:top_k]


if __name__ == "__main__":
    test_queries = [
        "hinh phat cho toi tang tru trai phep chat ma tuy",
        "nghe si nao bi bat vi su dung ma tuy",
        "quy dinh ve cai nghien bat buoc",
    ]
    for query in test_queries:
        print(f"\nQuery: {query}")
        for result in retrieve(query, top_k=3):
            print(f"[{result['score']:.3f}] [{result['source']}] {result['content'][:100]}...")
