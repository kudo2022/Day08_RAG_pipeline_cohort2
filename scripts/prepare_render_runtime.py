from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.task4_chunking_indexing import build_index
from src.task8_pageindex_vectorless import upload_documents


def main() -> None:
    chunks = build_index(force_rebuild=True)
    upload_documents(domain="procurement", allowed_types={"legal"})
    print(f"Prepared {len(chunks)} indexed chunks for Render runtime.")


if __name__ == "__main__":
    main()
