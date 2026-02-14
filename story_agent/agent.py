from __future__ import annotations

from pathlib import Path
from typing import Any

from .fetchers import SourceLoader, URLDocumentFetcher
from .formatter import InstagramFormatter
from .images import WikimediaImageFinder
from .insights import InsightBuilder
from .verifier import QuoteVerifier


class DoctrineInsightsAgent:
    """Coordinates ingestion, verification, insight extraction, and output."""

    def __init__(self):
        self.fetcher = URLDocumentFetcher()
        self.verifier = QuoteVerifier()
        self.builder = InsightBuilder(verifier=self.verifier)
        self.image_finder = WikimediaImageFinder()
        self.formatter = InstagramFormatter()

    def run(
        self,
        config_path: str | Path,
        output_dir: str | Path,
        max_insights: int = 5,
        attach_images: bool = True,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        config_path = Path(config_path)
        output_dir = Path(output_dir)

        sources = SourceLoader.load_yaml(config_path)
        if not sources:
            raise ValueError(
                "No sources were loaded from config. Add entries under the 'sources' key."
            )

        documents, fetch_warnings = self.fetcher.fetch_all(sources)
        warnings.extend(fetch_warnings)
        if not documents:
            raise ValueError("No source documents were fetched successfully.")

        insights = self.builder.build(documents=documents, max_insights=max_insights)
        if attach_images:
            try:
                warnings.extend(self.image_finder.assign_images(insights))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Image pipeline failed: {exc}")

        output_files = self.formatter.write(output_dir=output_dir, insights=insights, warnings=warnings)
        return {
            "sources_loaded": len(sources),
            "documents_fetched": len(documents),
            "insights_generated": len(insights),
            "warnings": warnings,
            "output_files": output_files,
        }

    def close(self) -> None:
        self.fetcher.close()
        self.image_finder.close()
