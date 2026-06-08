from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "landing" / "news"

ARTICLE_URLS: list[str] = []

SAMPLE_ARTICLES = [
    {
        "url": "https://vnexpress.net/ca-si-a-bi-bat-vi-ma-tuy-1234567.html",
        "title": "Ca si A bi bat vi ma tuy",
        "content_markdown": "Ca si A bi bat vi su dung ma tuy. " * 50,
    },
    {
        "url": "https://tuoitre.vn/nghe-si-b-bi-bat-20240608.htm",
        "title": "Nghe si B bi bat vi ma tuy",
        "content_markdown": "Nghe si B bi bat vi tang tru ma tuy. " * 45,
    },
    {
        "url": "https://thanhnien.vn/chuong-trinh-dai-han-ma-tuy-20240608.html",
        "title": "Chuong trinh dai han ma tuy lien quan nghe si",
        "content_markdown": "Chuong trinh nay bao ve viec truy quet ma tuy va xu ly vi pham. " * 42,
    },
    {
        "url": "https://dantri.com.vn/ma-tuy-nghe-si-c-20240608.htm",
        "title": "Nghe si C bi nghi su dung ma tuy",
        "content_markdown": "Thong tin ve viec giam sat nghe si C vi nghi su dung ma tuy. " * 45,
    },
    {
        "url": "https://zingnews.vn/ma-tuy-lien-quan-nghe-si-d-post123456.html",
        "title": "Tin ma tuy lien quan nghe si D",
        "content_markdown": "Bai bao ve vu viec ma tuy va nghe si D. " * 45,
    },
]


def setup_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


async def crawl_article(url: str) -> dict:
    """
    Crawl an article if Crawl4AI is installed, otherwise fall back to requests.
    """
    now = datetime.now(timezone.utc).isoformat()

    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            title = (
                getattr(result, "metadata", {}) or {}
            ).get("title", url.rsplit("/", 1)[-1])
            markdown = getattr(result, "markdown", "") or getattr(result, "text", "")
            return {
                "url": url,
                "title": title,
                "date_crawled": now,
                "content_markdown": markdown.strip(),
            }
    except Exception:
        pass

    try:
        import requests
        from bs4 import BeautifulSoup

        response = requests.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = (soup.title.string or url).strip() if soup.title else url
        paragraphs = [element.get_text(" ", strip=True) for element in soup.find_all("p")]
        markdown = "\n\n".join(paragraphs)
        return {
            "url": url,
            "title": title,
            "date_crawled": now,
            "content_markdown": markdown,
        }
    except Exception:
        return {
            "url": url,
            "title": url.rsplit("/", 1)[-1],
            "date_crawled": now,
            "content_markdown": "",
        }


def seed_sample_articles() -> list[Path]:
    setup_directory()
    written_paths: list[Path] = []
    for index, article in enumerate(SAMPLE_ARTICLES, start=1):
        payload = {
            "url": article["url"],
            "title": article["title"],
            "date_crawled": datetime.now(timezone.utc).isoformat(),
            "content_markdown": article["content_markdown"],
        }
        path = DATA_DIR / f"article_{index:02d}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        written_paths.append(path)
    return written_paths


async def crawl_all(urls: list[str] | None = None) -> list[Path]:
    setup_directory()
    urls = urls or ARTICLE_URLS
    if not urls:
        return seed_sample_articles()

    written_paths: list[Path] = []
    for index, url in enumerate(urls, start=1):
        article = await crawl_article(url)
        path = DATA_DIR / f"article_{index:02d}.json"
        path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
        written_paths.append(path)
    return written_paths


if __name__ == "__main__":
    paths = asyncio.run(crawl_all())
    for path in paths:
        print(f"Saved: {path}")
