from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.task1_collect_legal_docs import ensure_procurement_legal_docs
from src.task3_convert_markdown import convert_all
from src.task4_chunking_indexing import build_index
from src.task8_pageindex_vectorless import upload_documents


def main() -> None:
    docs = ensure_procurement_legal_docs(force_download=False)
    print(f"Downloaded or prepared {len(docs)} legal source documents.")

    converted = convert_all()
    print(f"Converted {len(converted)} files into Markdown.")

    chunks = build_index(force_rebuild=True)
    upload_documents(domain="procurement", allowed_types={"legal"})
    print(f"Indexed {len(chunks)} chunks for the procurement-law agent.")


if __name__ == "__main__":
    main()
