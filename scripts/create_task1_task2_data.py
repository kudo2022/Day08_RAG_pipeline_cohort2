from __future__ import annotations

import asyncio

from src.task1_collect_legal_docs import ensure_sample_legal_docs
from src.task2_crawl_news import crawl_all


def main() -> None:
    legal_docs = ensure_sample_legal_docs()
    news_files = asyncio.run(crawl_all())

    print("Legal documents:")
    for path in legal_docs:
        print(f"  - {path.name} ({path.stat().st_size} bytes)")

    print("News files:")
    for path in news_files:
        print(f"  - {path.name} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
