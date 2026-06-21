from __future__ import annotations

import json
import os
from pathlib import Path

from .rag_utils import extract_markdown_field, extract_year, first_heading, hash_embedding, normalize_text, searchable_text

STANDARDIZED_DIR = Path(__file__).resolve().parent.parent / "data" / "standardized"
INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "index"
VECTORSTORE_PATH = INDEX_DIR / "vector_store.json"

# Recursive chunking works well for mixed legal and news markdown because it
# preserves paragraph boundaries when possible, but still guarantees a hard
# length cap for search.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
CHUNKING_METHOD = "recursive"

# A small offline hash embedding keeps the project reproducible in a local
# classroom environment without downloading heavyweight models.
EMBEDDING_MODEL = "offline-hash-embedding"
EMBEDDING_DIM = 384

# Lightweight local JSON cache used as the vector store for this repository.
VECTOR_STORE = "local_json"
DEFAULT_DOMAIN = os.getenv("LEGAL_AGENT_DOMAIN", "procurement").strip().lower() or "procurement"

_INDEX_CACHE: list[dict] | None = None


def infer_domain(relative_path: str, content: str) -> str:
    sample = normalize_text(f"{relative_path}\n{content[:4000]}")

    procurement_keywords = (
        "dau thau",
        "nha thau",
        "nha dau tu",
        "goi thau",
        "ho so moi thau",
        "chi dinh thau",
    )
    if any(keyword in sample for keyword in procurement_keywords):
        return "procurement"

    narcotics_keywords = (
        "ma tuy",
        "chat cam",
        "cai nghien",
        "bo luat hinh su",
    )
    if any(keyword in sample for keyword in narcotics_keywords):
        return "drug_law"

    if "news/" in relative_path or "/news/" in relative_path:
        return "news"

    return "general"


def load_documents() -> list[dict]:
    """Load all markdown files from data/standardized/."""
    documents: list[dict] = []
    if not STANDARDIZED_DIR.exists():
        return documents

    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if md_file.name.startswith("."):
            continue

        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue

        title = extract_markdown_field(content, "Official title") or first_heading(content) or md_file.stem.replace("-", " ").title()
        relative_path = md_file.relative_to(STANDARDIZED_DIR).as_posix()
        domain = infer_domain(relative_path, content)
        documents.append(
            {
                "content": content,
                "metadata": {
                    "source": md_file.name,
                    "path": relative_path,
                    "type": md_file.parent.name,
                    "title": title,
                    "official_id": extract_markdown_field(content, "Official ID"),
                    "source_url": extract_markdown_field(content, "Official URL") or extract_markdown_field(content, "Source URL"),
                    "issued_date": extract_markdown_field(content, "Issued date"),
                    "effective_date": extract_markdown_field(content, "Effective date"),
                    "domain": domain,
                    "jurisdiction": "vietnam",
                    "year": extract_year(content, md_file.stem),
                },
            }
        )

    return documents


def _slice_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(text_length, start + CHUNK_SIZE)
        if end < text_length:
            window = text[start:end]
            candidate_breaks = [
                window.rfind("\n\n"),
                window.rfind("\n"),
                window.rfind(". "),
                window.rfind(" "),
            ]
            best_break = max(candidate_breaks)
            if best_break >= CHUNK_SIZE // 2:
                end = start + best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(end - CHUNK_OVERLAP, start + 1)
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents into chunks with overlap."""
    chunks: list[dict] = []

    for doc in documents:
        for chunk_index, chunk_text in enumerate(_slice_text(doc["content"])):
            chunk_metadata = dict(doc["metadata"])
            chunk_metadata["chunk_index"] = chunk_index
            chunk_metadata["chunk_id"] = f"{chunk_metadata.get('path', chunk_metadata['source'])}#{chunk_index}"
            chunks.append({"content": chunk_text, "metadata": chunk_metadata})

    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Attach a deterministic local embedding to every chunk."""
    embedded: list[dict] = []
    for chunk in chunks:
        enriched = {
            "content": chunk["content"],
            "metadata": dict(chunk["metadata"]),
            "embedding": hash_embedding(searchable_text(chunk), EMBEDDING_DIM),
        }
        embedded.append(enriched)
    return embedded


def index_to_vectorstore(chunks: list[dict]) -> Path:
    """Persist indexed chunks to a lightweight local JSON cache."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    VECTORSTORE_PATH.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    return VECTORSTORE_PATH


def build_index(force_rebuild: bool = False) -> list[dict]:
    """Build and cache the local vector store."""
    global _INDEX_CACHE
    if _INDEX_CACHE is not None and not force_rebuild:
        return [
            {
                "content": chunk["content"],
                "metadata": dict(chunk["metadata"]),
                "embedding": list(chunk["embedding"]),
            }
            for chunk in _INDEX_CACHE
        ]

    if VECTORSTORE_PATH.exists() and not force_rebuild:
        persisted_chunks = json.loads(VECTORSTORE_PATH.read_text(encoding="utf-8"))
        _INDEX_CACHE = persisted_chunks
        return [
            {
                "content": chunk["content"],
                "metadata": dict(chunk["metadata"]),
                "embedding": list(chunk["embedding"]),
            }
            for chunk in persisted_chunks
        ]

    documents = load_documents()
    chunks = chunk_documents(documents)
    indexed_chunks = embed_chunks(chunks)
    index_to_vectorstore(indexed_chunks)
    _INDEX_CACHE = indexed_chunks
    return [
        {
            "content": chunk["content"],
            "metadata": dict(chunk["metadata"]),
            "embedding": list(chunk["embedding"]),
        }
        for chunk in indexed_chunks
    ]


def run_pipeline() -> list[dict]:
    """Run the full indexing pipeline and return indexed chunks."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    indexed_chunks = build_index(force_rebuild=True)
    print(f"Loaded {len(load_documents())} documents")
    print(f"Created and indexed {len(indexed_chunks)} chunks")
    print(f"Saved local vector store to {VECTORSTORE_PATH}")
    return indexed_chunks


if __name__ == "__main__":
    run_pipeline()
