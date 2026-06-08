from __future__ import annotations

from .rag_utils import citation_label, normalize_text, split_sentences, tokenize
from .task9_retrieval_pipeline import retrieve

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

SYSTEM_PROMPT = """Answer in Vietnamese using only the retrieved context.
Every factual statement must include an inline citation.
If the context is insufficient, say "Toi khong the xac minh thong tin nay tu nguon hien co"."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Place the strongest chunks at the start and end of the prompt."""
    if len(chunks) <= 2:
        return list(chunks)

    front = [chunks[index] for index in range(0, len(chunks), 2)]
    back = [chunks[index] for index in range(1, len(chunks), 2)]
    back.reverse()
    return front + back


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a source-aware prompt context."""
    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", f"source_{index}")
        doc_type = metadata.get("type", "unknown")
        title = metadata.get("title") or source
        parts.append(
            f"[Document {index} | Source: {source} | Title: {title} | Type: {doc_type}]\n"
            f"{chunk.get('content', '').strip()}"
        )
    return "\n\n---\n\n".join(parts)


def _best_supporting_snippets(query: str, chunks: list[dict], limit: int = 3) -> list[tuple[str, dict]]:
    query_tokens = set(tokenize(query))
    ranked_snippets: list[tuple[float, str, dict]] = []

    for chunk in chunks:
        sentences = split_sentences(chunk.get("content", ""))
        if not sentences:
            sentences = [chunk.get("content", "").strip()]

        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue
            sentence_tokens = set(tokenize(cleaned))
            overlap = len(query_tokens & sentence_tokens) / max(len(query_tokens), 1) if query_tokens else 0.0
            score = 0.7 * overlap + 0.3 * float(chunk.get("score", 0.0))
            ranked_snippets.append((score, cleaned, chunk))

    ranked_snippets.sort(key=lambda item: item[0], reverse=True)

    selected: list[tuple[str, dict]] = []
    seen: set[str] = set()
    for score, sentence, chunk in ranked_snippets:
        if score <= 0:
            continue
        key = normalize_text(sentence)
        if key in seen:
            continue
        seen.add(key)
        selected.append((sentence[:260].strip(), chunk))
        if len(selected) >= limit:
            break

    return selected


def _generate_local_answer(query: str, chunks: list[dict]) -> str:
    if not chunks or chunks[0].get("score", 0.0) <= 0:
        return "Toi khong the xac minh thong tin nay tu nguon hien co."

    supporting_snippets = _best_supporting_snippets(query, chunks, limit=3)
    if not supporting_snippets:
        return "Toi khong the xac minh thong tin nay tu nguon hien co."

    statements: list[str] = []
    for snippet, chunk in supporting_snippets:
        label = citation_label(chunk)
        statements.append(f"{snippet} [{label}]")

    return " ".join(statements)


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """End-to-end local RAG generation with inline citations."""
    chunks = retrieve(query, top_k=top_k)
    reordered_chunks = reorder_for_llm(chunks)
    context = format_context(reordered_chunks)
    answer = _generate_local_answer(query, reordered_chunks)

    return {
        "answer": answer,
        "sources": reordered_chunks,
        "retrieval_source": reordered_chunks[0].get("source", "none") if reordered_chunks else "none",
        "context": context,
    }


if __name__ == "__main__":
    queries = [
        "Hinh phat cho toi tang tru trai phep chat ma tuy theo phap luat Viet Nam?",
        "Nhung nghe si nao bi bat vi lien quan toi ma tuy?",
        "Quy trinh cai nghien bat buoc la gi?",
    ]
    for query in queries:
        result = generate_with_citation(query)
        print(f"\nQ: {query}\nA: {result['answer']}")
