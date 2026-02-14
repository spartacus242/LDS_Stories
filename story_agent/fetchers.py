from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dt_parser

from .models import Document, SourceSpec
from .text_utils import normalize_text


DEFAULT_HEADERS = {
    "User-Agent": "LDSDoctrineInsightsAgent/1.0 (https://github.com/spartacus242/LDS_Stories)"
}


class SourceLoader:
    """Loads source configuration from a YAML file."""

    @staticmethod
    def load_yaml(path: str | Path) -> list[SourceSpec]:
        source_path = Path(path)
        payload = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
        raw_sources = payload.get("sources", [])
        sources: list[SourceSpec] = []
        for entry in raw_sources:
            if not entry.get("name") or not entry.get("url") or not entry.get("source_type"):
                continue
            sources.append(
                SourceSpec(
                    name=entry["name"],
                    url=entry["url"],
                    source_type=entry["source_type"],
                    author=entry.get("author"),
                    authority_office=entry.get("authority_office"),
                    tags=entry.get("tags", []),
                    published_hint=entry.get("published_hint"),
                )
            )
        return sources


class URLDocumentFetcher:
    """Fetches source URLs and extracts normalized text."""

    def __init__(self, timeout_seconds: int = 25):
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_all(self, sources: list[SourceSpec]) -> tuple[list[Document], list[str]]:
        documents: list[Document] = []
        warnings: list[str] = []

        for source in sources:
            try:
                response = self.session.get(source.url, timeout=self.timeout_seconds)
                response.raise_for_status()
                document = self._build_document(source, response)
                documents.append(document)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{source.name}: failed to fetch {source.url} ({exc})")
        return documents, warnings

    def _build_document(self, source: SourceSpec, response: requests.Response) -> Document:
        content_type = response.headers.get("Content-Type", "").lower()
        raw_text = self._decode_response_text(response)
        title: str | None = None
        published_at = self._parse_datetime(source.published_hint)

        if "html" in content_type or "<html" in raw_text.lower():
            soup = BeautifulSoup(raw_text, "html.parser")
            title = self._extract_title(soup) or source.name
            published_at = published_at or self._extract_datetime_from_html(soup)
            content = self._extract_text_from_html(soup)
        else:
            title = source.name
            content = normalize_text(raw_text)

        content = content.strip()
        if not content:
            raise ValueError("source had no parsable text content")

        doc_id_seed = f"{source.url}|{source.name}|{title}"
        doc_id = hashlib.sha1(doc_id_seed.encode("utf-8")).hexdigest()[:16]

        return Document(
            doc_id=doc_id,
            name=source.name,
            url=source.url,
            source_type=source.source_type,
            content=content,
            title=title,
            author=source.author,
            authority_office=source.authority_office,
            tags=source.tags,
            published_at=published_at,
            fetched_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _decode_response_text(response: requests.Response) -> str:
        if response.apparent_encoding:
            try:
                return response.content.decode(response.apparent_encoding, errors="replace")
            except LookupError:
                pass
        if response.encoding:
            try:
                return response.content.decode(response.encoding, errors="replace")
            except LookupError:
                pass
        return response.content.decode("utf-8", errors="replace")

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str | None:
        meta_title = soup.select_one('meta[property="og:title"]')
        if meta_title and meta_title.get("content"):
            return normalize_text(meta_title["content"])
        if soup.title and soup.title.text:
            return normalize_text(soup.title.text)
        h1 = soup.select_one("h1")
        if h1 and h1.text:
            return normalize_text(h1.text)
        return None

    @staticmethod
    def _extract_datetime_from_html(soup: BeautifulSoup) -> datetime | None:
        date_candidates = [
            ('meta[property="article:published_time"]', "content"),
            ('meta[name="publish-date"]', "content"),
            ("time[datetime]", "datetime"),
        ]
        for selector, field_name in date_candidates:
            node = soup.select_one(selector)
            if node and node.get(field_name):
                parsed = URLDocumentFetcher._parse_datetime(node.get(field_name))
                if parsed:
                    return parsed
        return None

    @staticmethod
    def _extract_text_from_html(soup: BeautifulSoup) -> str:
        for node in soup(["script", "style", "noscript", "svg", "form"]):
            node.decompose()

        # Remove common chrome that usually does not carry source text.
        for selector in ["header", "footer", "nav", "aside"]:
            for node in soup.select(selector):
                node.decompose()

        text_chunks: list[str] = []
        for element in soup.select("article p, main p, p, li, blockquote, h1, h2, h3"):
            candidate = normalize_text(element.get_text(" ", strip=True))
            if not candidate:
                continue
            if candidate.lower() in {"menu", "share", "sign in"}:
                continue
            text_chunks.append(candidate)

        if not text_chunks:
            body_text = normalize_text(soup.get_text(" ", strip=True))
            return body_text

        return normalize_text(" ".join(text_chunks))

    @staticmethod
    def _parse_datetime(raw_value: str | None) -> datetime | None:
        if not raw_value:
            return None
        try:
            parsed = dt_parser.parse(raw_value)
            if not parsed.tzinfo:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError, OverflowError):
            return None

    def close(self) -> None:
        self.session.close()
