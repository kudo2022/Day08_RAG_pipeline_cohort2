"""
Task 3 - convert files in data/landing/ into Markdown with MarkItDown.

This implementation follows the README requirements:
- scan all supported files under data/landing/
- convert them to Markdown
- save outputs under data/standardized/
- preserve subdirectories such as legal/ and news/
"""

from __future__ import annotations

import html
import json
from io import BytesIO
from pathlib import Path

from markitdown import MarkItDown

LANDING_DIR = Path(__file__).resolve().parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "standardized"

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".htm",
    ".html",
    ".json",
    ".md",
    ".txt",
}


def _discover_input_files(base_dir: Path) -> list[Path]:
    """Return supported source files under the landing directory."""
    return sorted(
        path
        for path in base_dir.rglob("*")
        if path.is_file()
        and not path.name.startswith(".")
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _pretty_title(path: Path) -> str:
    """Generate a readable title from a filename."""
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def _json_to_html(payload: object, source_path: Path) -> tuple[str, str | None, dict[str, str]]:
    """
    Build a simple HTML document from JSON news data so MarkItDown can
    convert it into clean Markdown instead of keeping raw JSON syntax.
    """
    if isinstance(payload, dict):
        title = str(payload.get("title") or _pretty_title(source_path))
        url = str(payload.get("url") or "")
        crawled = str(payload.get("date_crawled") or payload.get("date") or "")
        content = payload.get("content_markdown") or payload.get("content") or payload.get("body") or ""
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, indent=2)

        metadata = payload.get("metadata")
        metadata_lines: list[str] = []
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                metadata_lines.append(
                    f"<li><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</li>"
                )

        content_blocks: list[str] = []
        for block in str(content).splitlines():
            block = block.strip()
            if block:
                content_blocks.append(f"<p>{html.escape(block)}</p>")

        if not content_blocks:
            fallback = html.escape(json.dumps(payload, ensure_ascii=False, indent=2))
            content_blocks.append(f"<pre>{fallback}</pre>")

        html_parts = [
            "<html><body>",
            f"<h1>{html.escape(title)}</h1>",
        ]
        if url:
            safe_url = html.escape(url)
            html_parts.append(f'<p><strong>Source:</strong> <a href="{safe_url}">{safe_url}</a></p>')
        if crawled:
            html_parts.append(f"<p><strong>Crawled:</strong> {html.escape(crawled)}</p>")
        if metadata_lines:
            html_parts.append("<ul>")
            html_parts.extend(metadata_lines)
            html_parts.append("</ul>")
        html_parts.extend(content_blocks)
        html_parts.append("</body></html>")

        extra_fields = {}
        if url:
            extra_fields["Source URL"] = url
        if crawled:
            extra_fields["Crawled"] = crawled
        return "".join(html_parts), title, extra_fields

    title = _pretty_title(source_path)
    dumped = html.escape(json.dumps(payload, ensure_ascii=False, indent=2))
    html_doc = f"<html><body><h1>{html.escape(title)}</h1><pre>{dumped}</pre></body></html>"
    return html_doc, title, {}


def _convert_json_file(md: MarkItDown, source_path: Path) -> tuple[str, str | None, dict[str, str]]:
    """Convert JSON input by rendering it into HTML first."""
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    html_doc, title, extra_fields = _json_to_html(payload, source_path)
    result = md.convert_stream(BytesIO(html_doc.encode("utf-8")), file_extension=".html")
    return result.text_content, title, extra_fields


def _convert_regular_file(md: MarkItDown, source_path: Path) -> tuple[str, str | None, dict[str, str]]:
    """Convert a non-JSON file directly with MarkItDown."""
    result = md.convert(source_path)
    return result.text_content, None, {}


def _wrap_markdown(
    source_path: Path,
    markdown_body: str,
    title: str | None,
    extra_fields: dict[str, str],
    landing_dir: Path = LANDING_DIR,
) -> str:
    """Add a compact metadata header so every output is self-describing."""
    relative_source = source_path.relative_to(landing_dir).as_posix()
    lines = [
        f"# {title or _pretty_title(source_path)}",
        "",
        f"**Source file:** `{relative_source}`",
        f"**Original format:** `{source_path.suffix.lower()}`",
        "**Converted with:** `MarkItDown`",
    ]

    for key, value in extra_fields.items():
        lines.append(f"**{key}:** {value}")

    body = markdown_body.strip()
    if body:
        lines.extend(["", "---", "", body])

    return "\n".join(lines).strip() + "\n"


def _target_path_for(source_path: Path, output_dir: Path, landing_dir: Path = LANDING_DIR) -> Path:
    """Map a landing file to its standardized Markdown path."""
    relative_path = source_path.relative_to(landing_dir)
    return output_dir / relative_path.with_suffix(".md")


def convert_file(
    source_path: Path,
    output_dir: Path = OUTPUT_DIR,
    md: MarkItDown | None = None,
    landing_dir: Path = LANDING_DIR,
) -> Path:
    """Convert one file and return the written Markdown path."""
    md = md or MarkItDown()

    if source_path.suffix.lower() == ".json":
        markdown_body, title, extra_fields = _convert_json_file(md, source_path)
    else:
        markdown_body, title, extra_fields = _convert_regular_file(md, source_path)

    output_path = _target_path_for(source_path, output_dir, landing_dir=landing_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_markdown = _wrap_markdown(
        source_path,
        markdown_body,
        title,
        extra_fields,
        landing_dir=landing_dir,
    )
    output_path.write_text(final_markdown, encoding="utf-8")
    return output_path


def convert_legal_docs() -> list[Path]:
    """Convert all supported legal documents under data/landing/legal/."""
    md = MarkItDown()
    legal_dir = LANDING_DIR / "legal"
    files = [path for path in _discover_input_files(legal_dir)]
    return [convert_file(path, md=md, landing_dir=LANDING_DIR) for path in files]


def convert_news_articles() -> list[Path]:
    """Convert all supported news files under data/landing/news/."""
    md = MarkItDown()
    news_dir = LANDING_DIR / "news"
    files = [path for path in _discover_input_files(news_dir)]
    return [convert_file(path, md=md, landing_dir=LANDING_DIR) for path in files]


def convert_all(landing_dir: Path = LANDING_DIR, output_dir: Path = OUTPUT_DIR) -> list[Path]:
    """Convert every supported file in data/landing/ into Markdown."""
    md = MarkItDown()
    converted_paths: list[Path] = []
    failures: list[tuple[Path, Exception]] = []

    for source_path in _discover_input_files(landing_dir):
        try:
            output_path = convert_file(
                source_path,
                output_dir=output_dir,
                md=md,
                landing_dir=landing_dir,
            )
            converted_paths.append(output_path)
            print(f"[OK] {source_path.relative_to(landing_dir).as_posix()} -> {output_path.relative_to(output_dir).as_posix()}")
        except Exception as exc:  # pragma: no cover - best effort logging
            failures.append((source_path, exc))
            print(f"[FAIL] {source_path.relative_to(landing_dir).as_posix()}: {exc}")

    if not converted_paths:
        raise RuntimeError("No files were converted from data/landing/.")

    if failures:
        print(f"Converted {len(converted_paths)} files with {len(failures)} failures.")
    else:
        print(f"Converted {len(converted_paths)} files with no failures.")

    return converted_paths


if __name__ == "__main__":
    convert_all()
