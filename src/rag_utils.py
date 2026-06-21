from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_text(text: str) -> str:
    lowered = strip_accents(text).lower()
    return re.sub(r"\s+", " ", lowered).strip()


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(normalize_text(text))


def split_sentences(text: str) -> list[str]:
    plain = re.sub(r"\s+", " ", (text or "").replace("\r", " ").replace("\n", " ")).strip()
    if not plain:
        return []

    chunks = re.split(r"(?<=[.!?])\s+", plain)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def stable_hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)


def hash_embedding(text: str, dim: int) -> list[float]:
    vector = [0.0] * dim
    token_counts = Counter(tokenize(text))
    if not token_counts:
        return vector

    for token, count in token_counts.items():
        index = stable_hash(token) % dim
        sign = -1.0 if stable_hash(f"sign::{token}") % 2 else 1.0
        weight = 1.0 + math.log1p(count)
        vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def minmax_normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return [1.0 if high > 0 else 0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def first_heading(text: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def extract_year(*values: str) -> str:
    for value in values:
        match = YEAR_PATTERN.search(value or "")
        if match:
            return match.group(0)
    return ""


def extract_markdown_field(text: str, field_name: str) -> str:
    pattern = rf"^\*\*{re.escape(field_name)}:\*\*\s*(.+?)\s*$"
    match = re.search(pattern, text or "", flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def pretty_name(value: str) -> str:
    stem = Path(value).stem if value else "source"
    return stem.replace("-", " ").replace("_", " ").strip().title()


def unique_item_key(item: dict) -> str:
    metadata = item.get("metadata", {})
    source = metadata.get("path") or metadata.get("source") or "unknown"
    chunk_index = metadata.get("chunk_index", -1)
    prefix = normalize_text(item.get("content", ""))[:120]
    return f"{source}::{chunk_index}::{prefix}"


def metadata_matches(
    item_or_metadata: dict,
    domain: str | None = None,
    allowed_types: Iterable[str] | None = None,
) -> bool:
    metadata = item_or_metadata.get("metadata", item_or_metadata)
    if allowed_types:
        allowed = {value for value in allowed_types}
        if metadata.get("type") not in allowed:
            return False
    if domain and metadata.get("domain") != domain:
        return False
    return True


def searchable_text(item: dict) -> str:
    metadata = item.get("metadata", {})
    parts = [
        metadata.get("official_id", ""),
        metadata.get("title", ""),
        metadata.get("section", ""),
        item.get("content", ""),
    ]
    return "\n".join(part.strip() for part in parts if part and str(part).strip())


def citation_label(item: dict) -> str:
    metadata = item.get("metadata", {})
    official_id = metadata.get("official_id", "").strip()
    title = metadata.get("title") or pretty_name(metadata.get("source", "source"))
    base = official_id or title
    section = metadata.get("section", "").strip()
    year = metadata.get("year") or extract_year(metadata.get("source", ""), item.get("content", ""))

    if section and normalize_text(section) != normalize_text(title):
        return f"{base} - {section}"
    if official_id:
        return official_id
    return f"{base}, {year}" if year else base
