from __future__ import annotations

from typing import Any

import requests

from .models import ImageAsset, Insight


WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "LDSDoctrineInsightsAgent/1.0 (https://github.com/spartacus242/LDS_Stories)"
NON_PHOTO_OR_AI_MARKERS = {
    "ai-generated",
    "ai generated",
    "artificial intelligence",
    "midjourney",
    "stable diffusion",
    "dall-e",
    "illustration",
    "drawing",
    "painting",
    "digital art",
    "render",
    "vector",
    "cartoon",
}

CATEGORY_FALLBACK_QUERIES = {
    "prophetic_signal": [
        "world events photograph",
        "humanitarian aid photograph",
        "city skyline photograph",
    ],
    "authority_commonality": [
        "church congregation photograph",
        "family scripture study photograph",
        "christian worship photograph",
    ],
    "life_application": [
        "family prayer photograph",
        "community service photograph",
        "scripture reading photograph",
    ],
    "preparation": [
        "emergency preparedness kit photograph",
        "family planning photograph",
        "food storage photograph",
    ],
    "faith_evidence": [
        "sunrise landscape photograph",
        "hands praying photograph",
        "christian faith photograph",
    ],
}

GENERIC_FALLBACK_QUERIES = [
    "religious community photograph",
    "temple exterior photograph",
    "humanitarian service photograph",
]


class WikimediaImageFinder:
    """Finds likely non-AI images using Wikimedia Commons metadata."""

    def __init__(self, timeout_seconds: int = 20):
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def assign_images(self, insights: list[Insight]) -> list[str]:
        warnings: list[str] = []
        for insight in insights:
            attempted_queries = self._candidate_queries(insight)
            for query in attempted_queries:
                try:
                    asset = self.find_best_image(query=query)
                except Exception as exc:  # noqa: BLE001
                    warnings.append(
                        f"{insight.headline}: image query '{query}' failed ({exc})"
                    )
                    asset = None
                if asset:
                    insight.image = asset
                    break
            if not insight.image:
                warnings.append(
                    f"{insight.headline}: no qualifying Wikimedia image found after queries {attempted_queries}"
                )
        return warnings

    def find_best_image(self, query: str) -> ImageAsset | None:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 20,
            "prop": "imageinfo|categories|info",
            "iiprop": "url|extmetadata",
            "inprop": "url",
            "cllimit": "max",
            "format": "json",
        }
        response = self.session.get(WIKIMEDIA_API, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        pages = payload.get("query", {}).get("pages", {})
        for page in sorted(pages.values(), key=lambda item: item.get("index", 10_000)):
            asset = self._to_asset(page=page, query=query)
            if asset and asset.is_probably_non_ai:
                return asset
        return None

    def _to_asset(self, page: dict[str, Any], query: str) -> ImageAsset | None:
        imageinfo = (page.get("imageinfo") or [])
        if not imageinfo:
            return None
        info = imageinfo[0]
        image_url = info.get("url")
        if not image_url:
            return None

        ext_meta = info.get("extmetadata", {})
        description = self._meta_value(ext_meta, "ImageDescription")
        artist = self._meta_value(ext_meta, "Artist")
        license_name = self._meta_value(ext_meta, "LicenseShortName") or "Unknown"
        categories = " ".join(category.get("title", "") for category in page.get("categories", []))
        marker_text = " ".join([description, artist, categories, page.get("title", "")]).lower()
        has_marker = any(marker in marker_text for marker in NON_PHOTO_OR_AI_MARKERS)
        if has_marker:
            return ImageAsset(
                query=query,
                image_url=image_url,
                page_url=page.get("fullurl", image_url),
                title=page.get("title", "Wikimedia image"),
                attribution=artist or "Unknown author",
                license_name=license_name,
                is_probably_non_ai=False,
                rejection_reason="Metadata indicates AI-generated or non-photographic content.",
            )

        return ImageAsset(
            query=query,
            image_url=image_url,
            page_url=page.get("fullurl", image_url),
            title=page.get("title", "Wikimedia image"),
            attribution=artist or "Unknown author",
            license_name=license_name,
            is_probably_non_ai=True,
        )

    @staticmethod
    def _meta_value(ext_meta: dict[str, Any], key: str) -> str:
        value = ext_meta.get(key, {})
        if isinstance(value, dict):
            return str(value.get("value", "")).strip()
        return str(value or "").strip()

    @staticmethod
    def _build_query(insight: Insight) -> str:
        terms = insight.key_terms[:4]
        if not terms:
            terms = [insight.category]
        return " ".join(terms) + " photograph"

    def _candidate_queries(self, insight: Insight) -> list[str]:
        queries = [self._build_query(insight)]
        queries.extend(CATEGORY_FALLBACK_QUERIES.get(insight.category, []))
        queries.extend(GENERIC_FALLBACK_QUERIES)
        deduped: list[str] = []
        seen = set()
        for query in queries:
            marker = query.lower().strip()
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(query)
        return deduped

    def close(self) -> None:
        self.session.close()
