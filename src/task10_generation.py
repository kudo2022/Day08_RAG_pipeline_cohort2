from __future__ import annotations

import os

from dotenv import load_dotenv

from .rag_utils import citation_label, normalize_text, split_sentences, tokenize
from .task4_chunking_indexing import DEFAULT_DOMAIN
from .task9_retrieval_pipeline import retrieve

load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.2
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

SYSTEM_PROMPT = """Ban la ProcurementLawAgent.
Tra loi bang tieng Viet, ngan gon, ro rang, uu tien chinh xac.
Chi duoc dua vao context da truy xuat.
Moi nhan dinh thuc te phai co citation inline.
Neu context khong du, phai noi ro khong the xac minh tu nguon hien co.
Khong tu y bo sung dieu, khoan, nguong gia tri neu context khong neu ro.
Neu cau hoi lien quan den moc thoi gian hay hieu luc, uu tien neu ro ngay thang cu the."""


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
        official_id = metadata.get("official_id", "").strip()
        section = metadata.get("section", "").strip()
        source_url = metadata.get("source_url", "").strip()
        effective_date = metadata.get("effective_date", "").strip()

        header_parts = [f"Document {index}", f"Source: {source}", f"Title: {title}", f"Type: {doc_type}"]
        if official_id:
            header_parts.append(f"Official ID: {official_id}")
        if section:
            header_parts.append(f"Section: {section}")
        if effective_date:
            header_parts.append(f"Effective date: {effective_date}")
        if source_url:
            header_parts.append(f"Official URL: {source_url}")

        parts.append(f"[{' | '.join(header_parts)}]\n{chunk.get('content', '').strip()}")
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


def _format_history(conversation_history: list[dict] | None) -> str:
    if not conversation_history:
        return ""

    recent_turns = conversation_history[-6:]
    lines = ["History:"]
    for turn in recent_turns:
        role = "User" if turn.get("role") == "user" else "Assistant"
        content = (turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_prompt(query: str, context: str, conversation_history: list[dict] | None = None) -> str:
    history_block = _format_history(conversation_history)
    prompt_parts = [SYSTEM_PROMPT]
    if history_block:
        prompt_parts.extend(["", history_block])
    prompt_parts.extend(
        [
            "",
            f"Current question: {query}",
            "",
            "Retrieved legal context:",
            context or "(empty)",
            "",
            "Instructions:",
            "- Tra loi bang tieng Viet.",
            "- Neu co nhieu truong hop, tach ro tung truong hop.",
            "- Moi doan thong tin quan trong phai co citation inline nhu [74/VBHN-VPQH] hoac [24/2024/ND-CP].",
            "- Neu context khong du de ket luan, phai noi ro dieu do.",
        ]
    )
    return "\n".join(prompt_parts)


def _get_gemini_client():
    if not GEMINI_API_KEY:
        return None

    try:
        from google import genai
    except Exception:
        return None

    return genai.Client(api_key=GEMINI_API_KEY)


def _generate_gemini_answer(
    query: str,
    chunks: list[dict],
    context: str,
    conversation_history: list[dict] | None = None,
) -> str:
    if not chunks:
        return "Toi khong the xac minh thong tin nay tu nguon hien co."

    client = _get_gemini_client()
    if client is None:
        return _generate_local_answer(query, chunks)

    prompt = _build_prompt(query=query, context=context, conversation_history=conversation_history)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = (response.text or "").strip()
        return text or _generate_local_answer(query, chunks)
    except Exception:
        return _generate_local_answer(query, chunks)


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    conversation_history: list[dict] | None = None,
    retrieval_query: str | None = None,
    domain: str = DEFAULT_DOMAIN,
) -> dict:
    """End-to-end RAG generation with Gemini and inline citations."""
    effective_query = retrieval_query or query
    client_available = _get_gemini_client() is not None
    chunks = retrieve(
        effective_query,
        top_k=top_k,
        domain=domain,
        allowed_types={"legal"},
    )
    reordered_chunks = reorder_for_llm(chunks)
    context = format_context(reordered_chunks)
    answer = _generate_gemini_answer(
        query=query,
        chunks=reordered_chunks,
        context=context,
        conversation_history=conversation_history,
    )

    return {
        "answer": answer,
        "sources": reordered_chunks,
        "retrieval_source": reordered_chunks[0].get("source", "none") if reordered_chunks else "none",
        "context": context,
        "model": GEMINI_MODEL if client_available else "local-fallback",
        "domain": domain,
        "query_used_for_retrieval": effective_query,
    }


if __name__ == "__main__":
    queries = [
        "Chi dinh thau duoc ap dung trong truong hop nao?",
        "Van ban nao dang la ban hop nhat moi hon cho Luat Dau thau?",
        "Nghi dinh nao huong dan lua chon nha thau?",
    ]
    for query in queries:
        result = generate_with_citation(query)
        print(f"\nQ: {query}\nA: {result['answer']}")
