from __future__ import annotations

from typing import Any

import requests

from .models import ImageAsset, Insight


WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
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


class WikimediaImageFinder:
    """Finds likely non-AI images using Wikimedia Commons metadata."""

    def __init__(self, timeout_seconds: int = 20):
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "LDSDoctrineInsightsAgent/1.0 (+https://example.invalid/contact)"}
        )

    def assign_images(self, insights: list[Insight]) -> list[str]:
        warnings: list[str] = []
        for insight in insights:
            query = self._build_query(insight)
            asset = self.find_best_image(query=query)
            if asset:
                insight.image = asset
            else:
                warnings.append(
                    f"{insight.headline}: no qualifying Wikimedia image found for query '{query}'"
                )
        return warnings

    def find_best_image(self, query: str) -> ImageAsset | None:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
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
        for page in pages.values():
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
        return " ".join(terms)

    def close(self) -> None:
        self.session.close()
