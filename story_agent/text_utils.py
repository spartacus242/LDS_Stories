from __future__ import annotations

import re
from collections import Counter


DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
    "we",
    "our",
    "you",
    "your",
    "they",
    "their",
    "them",
    "this",
    "those",
    "these",
    "i",
    "me",
    "my",
    "mine",
    "or",
    "if",
    "then",
    "there",
    "here",
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "not",
    "but",
    "can",
    "could",
    "should",
    "would",
    "may",
    "might",
    "do",
    "does",
    "did",
    "have",
    "had",
    "having",
}


def normalize_text(value: str) -> str:
    """Normalize whitespace and trim strings."""
    return re.sub(r"\s+", " ", value).strip()


def normalize_for_match(value: str) -> str:
    """Normalize text for case-insensitive quote matching."""
    normalized = value.lower()
    normalized = normalized.replace("\u2019", "'").replace("\u2018", "'")
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = re.sub(r"[^a-z0-9\s']", " ", normalized)
    return normalize_text(normalized)


def split_sentences(text: str) -> list[str]:
    """A lightweight sentence splitter good enough for short documents."""
    chunks = re.split(r"(?<=[.!?])\s+", normalize_text(text))
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']{3,}", text.lower())


def extract_keywords(text: str, limit: int = 12, extra_stopwords: set[str] | None = None) -> list[str]:
    stopwords = set(DEFAULT_STOPWORDS)
    if extra_stopwords:
        stopwords.update(extra_stopwords)
    tokens = [token for token in tokenize_words(text) if token not in stopwords]
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(limit)]


def trim_to_word_count(text: str, max_words: int) -> str:
    words = normalize_text(text).split(" ")
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(".,;: ") + "..."
