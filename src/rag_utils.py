from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

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


def pretty_name(value: str) -> str:
    stem = Path(value).stem if value else "source"
    return stem.replace("-", " ").replace("_", " ").strip().title()


def unique_item_key(item: dict) -> str:
    metadata = item.get("metadata", {})
    source = metadata.get("path") or metadata.get("source") or "unknown"
    chunk_index = metadata.get("chunk_index", -1)
    prefix = normalize_text(item.get("content", ""))[:120]
    return f"{source}::{chunk_index}::{prefix}"


def citation_label(item: dict) -> str:
    metadata = item.get("metadata", {})
    title = metadata.get("title") or pretty_name(metadata.get("source", "source"))
    year = metadata.get("year") or extract_year(metadata.get("source", ""), item.get("content", ""))
    return f"{title}, {year}" if year else title
