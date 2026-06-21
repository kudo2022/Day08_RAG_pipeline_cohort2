from __future__ import annotations

from dataclasses import dataclass, field

from .rag_utils import normalize_text
from .task4_chunking_indexing import DEFAULT_DOMAIN
from .task10_generation import generate_with_citation


def _looks_like_follow_up(query: str) -> bool:
    normalized = normalize_text(query)
    follow_up_markers = (
        "con truong hop nay",
        "truong hop nay",
        "neu vay",
        "the con",
        "con neu",
        "ap dung voi",
        "cai nay",
        "van ban nao",
        "dieu nao",
        "khoan nao",
    )
    return len(normalized.split()) <= 9 or any(marker in normalized for marker in follow_up_markers)


@dataclass
class ProcurementLawAgent:
    top_k: int = 5
    domain: str = DEFAULT_DOMAIN
    memory: list[dict] = field(default_factory=list)

    def reset(self) -> None:
        self.memory.clear()

    def _standalone_retrieval_query(self, query: str) -> str:
        if not self.memory or not _looks_like_follow_up(query):
            return query

        last_user_question = next(
            (turn["content"] for turn in reversed(self.memory) if turn.get("role") == "user"),
            "",
        )
        if not last_user_question:
            return query

        return f"{last_user_question}\nCau hoi tiep theo: {query}"

    def answer(self, query: str) -> dict:
        retrieval_query = self._standalone_retrieval_query(query)
        result = generate_with_citation(
            query=query,
            top_k=self.top_k,
            conversation_history=self.memory,
            retrieval_query=retrieval_query,
            domain=self.domain,
        )
        self.memory.append({"role": "user", "content": query})
        self.memory.append({"role": "assistant", "content": result["answer"]})
        return result
