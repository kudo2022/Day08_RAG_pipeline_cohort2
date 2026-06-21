from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from .rag_utils import clamp, metadata_matches, normalize_text, tokenize
from .task4_chunking_indexing import DEFAULT_DOMAIN, INDEX_DIR, load_documents

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
PAGEINDEX_CACHE_PATH = INDEX_DIR / "pageindex_manifest.json"


def _split_sections(document: dict) -> list[dict]:
    sections: list[dict] = []
    current_heading = document["metadata"].get("title") or document["metadata"].get("source", "Section")
    current_lines: list[str] = []

    for line in document["content"].splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_lines:
                sections.append(
                    {
                        "heading": current_heading,
                        "content": "\n".join(current_lines).strip(),
                        "metadata": dict(document["metadata"]),
                    }
                )
                current_lines = []
            current_heading = stripped.lstrip("#").strip() or current_heading
        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            {
                "heading": current_heading,
                "content": "\n".join(current_lines).strip(),
                "metadata": dict(document["metadata"]),
            }
        )

    return [section for section in sections if section["content"]]


def upload_documents(
    domain: str | None = DEFAULT_DOMAIN,
    allowed_types: set[str] | None = None,
) -> list[dict]:
    """
    Build a small structural manifest that mimics PageIndex's document view.

    If a real PAGEINDEX_API_KEY is configured, this function can be extended to
    call the official SDK. For local coursework we keep an offline manifest.
    """
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for document in load_documents():
        if not metadata_matches(document, domain=domain, allowed_types=allowed_types):
            continue
        manifest.extend(_split_sections(document))

    PAGEINDEX_CACHE_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _load_manifest(
    domain: str | None = DEFAULT_DOMAIN,
    allowed_types: set[str] | None = None,
) -> list[dict]:
    if PAGEINDEX_CACHE_PATH.exists():
        manifest = json.loads(PAGEINDEX_CACHE_PATH.read_text(encoding="utf-8"))
        filtered = [
            section
            for section in manifest
            if metadata_matches(section, domain=domain, allowed_types=allowed_types)
        ]
        if filtered:
            return filtered
    return upload_documents(domain=domain, allowed_types=allowed_types)


def pageindex_search(
    query: str,
    top_k: int = 5,
    domain: str | None = DEFAULT_DOMAIN,
    allowed_types: set[str] | None = None,
) -> list[dict]:
    """Offline structural retrieval used as the vectorless fallback."""
    if top_k <= 0:
        return []

    query_tokens = set(tokenize(query))
    query_text = normalize_text(query)
    if not query_tokens:
        return []

    results: list[dict] = []
    for section in _load_manifest(domain=domain, allowed_types=allowed_types):
        heading_tokens = set(tokenize(section["heading"]))
        content_tokens = set(tokenize(section["content"]))
        coverage = len(query_tokens & content_tokens) / len(query_tokens)
        heading_bonus = len(query_tokens & heading_tokens) / len(query_tokens)
        phrase_bonus = 0.15 if query_text and query_text in normalize_text(section["content"]) else 0.0
        score = clamp(0.6 * coverage + 0.25 * heading_bonus + phrase_bonus)
        if score <= 0:
            continue

        metadata = dict(section["metadata"])
        metadata["section"] = section["heading"]
        excerpt = section["content"][:500].strip()
        results.append(
            {
                "content": excerpt,
                "score": float(score),
                "metadata": metadata,
                "source": "pageindex",
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


if __name__ == "__main__":
    upload_documents()
    for result in pageindex_search("hinh phat su dung ma tuy", top_k=3):
        print(f"[{result['score']:.3f}] {result['metadata'].get('source')} -> {result['content'][:100]}...")
