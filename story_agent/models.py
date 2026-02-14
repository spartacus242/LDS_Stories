from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class SourceSpec:
    """Represents a single source configured for ingestion."""

    name: str
    url: str
    source_type: str
    author: str | None = None
    authority_office: str | None = None
    tags: list[str] = field(default_factory=list)
    published_hint: str | None = None


@dataclass(slots=True)
class Document:
    """Normalized source document text and metadata."""

    doc_id: str
    name: str
    url: str
    source_type: str
    content: str
    title: str | None = None
    author: str | None = None
    authority_office: str | None = None
    tags: list[str] = field(default_factory=list)
    published_at: datetime | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.published_at:
            payload["published_at"] = self.published_at.isoformat()
        payload["fetched_at"] = self.fetched_at.isoformat()
        return payload


@dataclass(slots=True)
class Citation:
    """A citation entry tied to an insight claim."""

    doc_id: str
    title: str
    url: str
    quote: str
    verification: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QuoteVerificationResult:
    """Result of checking whether a quote exists in a source document."""

    quote: str
    doc_id: str
    is_exact_match: bool
    is_close_match: bool
    best_snippet: str
    score: float
    notes: str

    @property
    def confidence_label(self) -> str:
        if self.is_exact_match:
            return "high"
        if self.is_close_match:
            return "medium"
        return "low"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ImageAsset:
    """A candidate image and attribution details."""

    query: str
    image_url: str
    page_url: str
    title: str
    attribution: str
    license_name: str
    is_probably_non_ai: bool
    rejection_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Insight:
    """Final normalized story card ready for Instagram-style output."""

    category: str
    headline: str
    story: str
    action_step: str
    confidence: str
    uncertainty_note: str
    key_terms: list[str]
    citations: list[Citation] = field(default_factory=list)
    image: ImageAsset | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["citations"] = [citation.to_dict() for citation in self.citations]
        payload["image"] = self.image.to_dict() if self.image else None
        return payload
