from __future__ import annotations

import os
import uuid
from functools import lru_cache
from threading import Lock
from typing import Any

from flask import Flask, jsonify, make_response, render_template, request

from src.procurement_law_agent import ProcurementLawAgent
from src.task1_collect_legal_docs import ensure_procurement_legal_docs
from src.task3_convert_markdown import convert_all
from src.task4_chunking_indexing import STANDARDIZED_DIR, VECTORSTORE_PATH, build_index
from src.task8_pageindex_vectorless import PAGEINDEX_CACHE_PATH, upload_documents
from src.task10_generation import GEMINI_API_KEY, GEMINI_MODEL


app = Flask(__name__)
app.json.ensure_ascii = False

SESSION_COOKIE_NAME = "procurement_law_session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 7

REQUIRED_PROCUREMENT_MARKDOWN = [
    "74-vbhn-vpqh-luat-dau-thau-hop-nhat-2026.md",
    "24-2024-nd-cp-lua-chon-nha-thau.md",
    "17-2025-nd-cp-sua-doi-nghi-dinh-dau-thau.md",
    "23-2024-nd-cp-lua-chon-nha-dau-tu-theo-nganh.md",
    "115-2024-nd-cp-lua-chon-nha-dau-tu-du-an-su-dung-dat.md",
]

SUGGESTED_QUESTIONS = [
    "Chi dinh thau duoc ap dung trong truong hop nao?",
    "Nghi dinh nao dang huong dan Luat Dau thau hien nay?",
    "Khi nao phai dau thau qua mang?",
    "Lua chon nha dau tu du an su dung dat can doi chieu van ban nao?",
]

AGENT_SESSIONS: dict[str, ProcurementLawAgent] = {}
SESSION_LOCK = Lock()


def _has_prepared_procurement_markdown() -> bool:
    legal_dir = STANDARDIZED_DIR / "legal"
    return legal_dir.exists() and all((legal_dir / filename).exists() for filename in REQUIRED_PROCUREMENT_MARKDOWN)


def _count_existing_markdown_files() -> int:
    if not STANDARDIZED_DIR.exists():
        return 0
    return len(list(STANDARDIZED_DIR.rglob("*.md")))


@lru_cache(maxsize=1)
def get_knowledge_base_status() -> dict[str, Any]:
    try:
        docs = ensure_procurement_legal_docs(force_download=False)
        if _has_prepared_procurement_markdown():
            converted_count = _count_existing_markdown_files()
        else:
            converted_count = len(convert_all())

        chunks = build_index(force_rebuild=not VECTORSTORE_PATH.exists())
        if not PAGEINDEX_CACHE_PATH.exists():
            upload_documents(domain="procurement", allowed_types={"legal"})

        return {
            "documents": len(docs),
            "converted": converted_count,
            "chunks": len(chunks),
            "ready": True,
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - defensive UI handling
        return {
            "documents": 0,
            "converted": 0,
            "chunks": 0,
            "ready": False,
            "error": str(exc),
        }


def unique_sources(sources: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for source in sources:
        metadata = source.get("metadata", {})
        key = metadata.get("official_id") or metadata.get("path") or metadata.get("source")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def _serialize_sources(sources: list[dict]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in unique_sources(sources):
        metadata = source.get("metadata", {})
        items.append(
            {
                "title": metadata.get("title") or metadata.get("source") or "Nguon phap ly",
                "official_id": metadata.get("official_id") or "n/a",
                "effective_date": metadata.get("effective_date") or "n/a",
                "source_url": metadata.get("source_url") or "",
                "score": round(float(source.get("score", 0.0)), 3),
                "snippet": source.get("content", "")[:900],
            }
        )
    return items


def _serialize_history(agent: ProcurementLawAgent) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for turn in agent.memory:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history


def _resolve_session_id() -> tuple[str, bool]:
    session_id = (request.cookies.get(SESSION_COOKIE_NAME) or "").strip()
    if session_id:
        return session_id, False
    return uuid.uuid4().hex, True


def _get_agent(session_id: str) -> ProcurementLawAgent:
    with SESSION_LOCK:
        agent = AGENT_SESSIONS.get(session_id)
        if agent is None:
            agent = ProcurementLawAgent()
            AGENT_SESSIONS[session_id] = agent
        return agent


def _reset_agent(session_id: str) -> None:
    with SESSION_LOCK:
        AGENT_SESSIONS.pop(session_id, None)


def _apply_session_cookie(response, session_id: str, is_new_session: bool):
    if is_new_session:
        response.set_cookie(
            SESSION_COOKIE_NAME,
            session_id,
            max_age=SESSION_COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )
    return response


@app.get("/")
def index():
    session_id, is_new_session = _resolve_session_id()
    agent = _get_agent(session_id)
    bootstrap = {
        "status": get_knowledge_base_status(),
        "geminiEnabled": bool(GEMINI_API_KEY),
        "modelLabel": GEMINI_MODEL if GEMINI_API_KEY else "local-fallback",
        "suggestedQuestions": SUGGESTED_QUESTIONS,
        "history": _serialize_history(agent),
        "scopeText": (
            "Tra loi ve Luat Dau thau hop nhat 74/VBHN-VPQH va cac nghi dinh "
            "24/2024/ND-CP, 17/2025/ND-CP, 23/2024/ND-CP, 115/2024/ND-CP."
        ),
    }
    response = make_response(render_template("index.html", bootstrap=bootstrap))
    return _apply_session_cookie(response, session_id, is_new_session)


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("message") or "").strip()
    if not prompt:
        return jsonify({"error": "Vui long nhap cau hoi truoc khi gui."}), 400

    status = get_knowledge_base_status()
    if not status["ready"]:
        return jsonify({"error": f"Knowledge base chua san sang: {status['error']}"}), 503

    session_id, is_new_session = _resolve_session_id()
    agent = _get_agent(session_id)

    try:
        result = agent.answer(prompt)
    except Exception as exc:  # pragma: no cover - defensive UI handling
        return jsonify({"error": f"He thong tra loi dang gap loi: {exc}"}), 500

    response = jsonify(
        {
            "answer": result["answer"],
            "sources": _serialize_sources(result["sources"]),
            "model": result["model"],
            "retrievalQuery": result["query_used_for_retrieval"],
        }
    )
    return _apply_session_cookie(response, session_id, is_new_session)


@app.post("/api/reset")
def reset_chat():
    session_id, is_new_session = _resolve_session_id()
    _reset_agent(session_id)
    response = jsonify({"ok": True})
    return _apply_session_cookie(response, session_id, is_new_session)


@app.get("/healthz")
def healthcheck():
    status = get_knowledge_base_status()
    http_status = 200 if status["ready"] else 500
    return jsonify({"ok": status["ready"], "status": status}), http_status


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
