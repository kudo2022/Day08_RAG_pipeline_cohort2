from __future__ import annotations

from .rag_utils import clamp, cosine_similarity, hash_embedding, minmax_normalize, normalize_text, tokenize, unique_item_key
from .task4_chunking_indexing import EMBEDDING_DIM


def _ensure_embedding(candidate: dict) -> list[float]:
    embedding = candidate.get("embedding")
    if embedding:
        return list(embedding)
    return hash_embedding(candidate.get("content", ""), EMBEDDING_DIM)


def rerank_cross_encoder(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """
    Lightweight local reranker.

    This mimics cross-encoder behavior by rescoring candidates with query-term
    overlap plus embedding similarity, which is reliable for offline testing.
    """
    if top_k <= 0 or not candidates:
        return []

    query_tokens = set(tokenize(query))
    query_embedding = hash_embedding(query, EMBEDDING_DIM)
    query_text = normalize_text(query)
    reranked: list[dict] = []

    for candidate in candidates:
        enriched = dict(candidate)
        enriched["metadata"] = dict(candidate.get("metadata", {}))
        enriched["embedding"] = _ensure_embedding(candidate)

        candidate_tokens = set(tokenize(candidate.get("content", "")))
        overlap = len(query_tokens & candidate_tokens) / max(len(query_tokens), 1) if query_tokens else 0.0
        semantic = cosine_similarity(query_embedding, enriched["embedding"])
        phrase_bonus = 0.1 if query_text and query_text in normalize_text(candidate.get("content", "")) else 0.0
        base_score = float(candidate.get("score", 0.0))

        enriched["score"] = clamp(0.45 * overlap + 0.35 * semantic + 0.20 * base_score + phrase_bonus)
        reranked.append(enriched)

    reranked.sort(key=lambda item: item["score"], reverse=True)

    deduped: list[dict] = []
    seen: set[str] = set()
    for item in reranked:
        key = unique_item_key(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= top_k:
            break

    return deduped


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """Maximal Marginal Relevance for diversity-aware reranking."""
    if top_k <= 0 or not candidates:
        return []

    enriched_candidates = []
    for candidate in candidates:
        enriched = dict(candidate)
        enriched["metadata"] = dict(candidate.get("metadata", {}))
        enriched["embedding"] = _ensure_embedding(candidate)
        enriched_candidates.append(enriched)

    selected_indices: list[int] = []
    remaining_indices = list(range(len(enriched_candidates)))

    while remaining_indices and len(selected_indices) < top_k:
        best_index = remaining_indices[0]
        best_score = float("-inf")

        for index in remaining_indices:
            relevance = cosine_similarity(query_embedding, enriched_candidates[index]["embedding"])
            diversity_penalty = 0.0
            if selected_indices:
                diversity_penalty = max(
                    cosine_similarity(
                        enriched_candidates[index]["embedding"],
                        enriched_candidates[selected_index]["embedding"],
                    )
                    for selected_index in selected_indices
                )
            mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
            if mmr_score > best_score:
                best_score = mmr_score
                best_index = index

        selected_indices.append(best_index)
        remaining_indices.remove(best_index)
        enriched_candidates[best_index]["score"] = clamp((best_score + 1.0) / 2.0)

    return [enriched_candidates[index] for index in selected_indices]


def rerank_rrf(ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion for merging multiple ranked lists."""
    if top_k <= 0:
        return []

    raw_scores: dict[str, float] = {}
    item_map: dict[str, dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            key = unique_item_key(item)
            raw_scores[key] = raw_scores.get(key, 0.0) + 1.0 / (k + rank)
            current = item_map.get(key)
            if current is None or item.get("score", 0.0) > current.get("score", 0.0):
                saved = dict(item)
                saved["metadata"] = dict(item.get("metadata", {}))
                if "embedding" in item:
                    saved["embedding"] = list(item["embedding"])
                item_map[key] = saved

    ranked_keys = sorted(raw_scores, key=raw_scores.get, reverse=True)
    normalized_scores = minmax_normalize([raw_scores[key] for key in ranked_keys])

    results: list[dict] = []
    for key, normalized_score in zip(ranked_keys, normalized_scores):
        item = dict(item_map[key])
        item["metadata"] = dict(item.get("metadata", {}))
        if "embedding" in item:
            item["embedding"] = list(item["embedding"])
        item["score"] = float(normalized_score)
        results.append(item)
        if len(results) >= top_k:
            break

    return results


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "cross_encoder",
) -> list[dict]:
    """Unified reranking interface."""
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    if method == "mmr":
        return rerank_mmr(hash_embedding(query, EMBEDDING_DIM), candidates, top_k)
    if method == "rrf":
        return rerank_rrf([candidates], top_k)
    raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    dummy_candidates = [
        {"content": "Dieu 248 quy dinh toi tang tru trai phep chat ma tuy", "score": 0.8, "metadata": {}},
        {"content": "Nghe si bi bat vi su dung ma tuy", "score": 0.6, "metadata": {}},
        {"content": "Python programming language", "score": 0.2, "metadata": {}},
    ]
    for result in rerank("hinh phat tang tru ma tuy", dummy_candidates, top_k=2):
        print(f"[{result['score']:.3f}] {result['content']}")
