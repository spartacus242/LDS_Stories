from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Insight


class InstagramFormatter:
    """Formats insight objects into short Instagram-style cards."""

    @staticmethod
    def to_story_card(insight: Insight) -> dict[str, Any]:
        return {
            "category": insight.category,
            "headline": insight.headline,
            "story": insight.story,
            "action_step": insight.action_step,
            "confidence": insight.confidence,
            "uncertainty_note": insight.uncertainty_note,
            "citations": [citation.to_dict() for citation in insight.citations],
            "image": insight.image.to_dict() if insight.image else None,
        }

    @staticmethod
    def to_caption(insight: Insight) -> str:
        lines = [
            insight.headline.upper(),
            "",
            insight.story,
            "",
            f"Action: {insight.action_step}",
            f"Confidence: {insight.confidence}",
            f"Uncertainty note: {insight.uncertainty_note}",
            "",
            "Sources:",
        ]
        for citation in insight.citations:
            lines.append(
                f"- {citation.title} ({citation.url}) | verification={citation.verification}"
            )
        if insight.image:
            lines.extend(
                [
                    "",
                    f"Image: {insight.image.image_url}",
                    f"Image page: {insight.image.page_url}",
                    f"Image attribution: {insight.image.attribution}",
                    f"Image license: {insight.image.license_name}",
                ]
            )
        return "\n".join(lines)

    def write(self, output_dir: str | Path, insights: list[Insight], warnings: list[str]) -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        cards = [self.to_story_card(insight) for insight in insights]
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "card_count": len(cards),
            "warnings": warnings,
            "cards": cards,
        }

        json_path = output_path / f"insights_{timestamp}.json"
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

        md_path = output_path / f"insights_{timestamp}.md"
        markdown_blocks = []
        for idx, insight in enumerate(insights, start=1):
            markdown_blocks.append(f"## {idx}. {insight.headline}")
            markdown_blocks.append("")
            markdown_blocks.append(insight.story)
            markdown_blocks.append("")
            markdown_blocks.append(f"**Action:** {insight.action_step}")
            markdown_blocks.append(f"**Confidence:** {insight.confidence}")
            markdown_blocks.append(f"**Uncertainty:** {insight.uncertainty_note}")
            markdown_blocks.append("")
            markdown_blocks.append("**Citations**")
            for citation in insight.citations:
                markdown_blocks.append(
                    f"- [{citation.title}]({citation.url}) | quote check: {citation.verification}"
                )
                markdown_blocks.append(f"  - Quote: \"{citation.quote}\"")
            if insight.image:
                markdown_blocks.append("")
                markdown_blocks.append(
                    f"**Image:** [{insight.image.title}]({insight.image.page_url}) ({insight.image.image_url})"
                )
                markdown_blocks.append(
                    f"- Attribution: {insight.image.attribution} | License: {insight.image.license_name}"
                )
            markdown_blocks.append("\n---\n")
        if warnings:
            markdown_blocks.append("## Pipeline Warnings")
            markdown_blocks.append("")
            for warning in warnings:
                markdown_blocks.append(f"- {warning}")
            markdown_blocks.append("")
        md_path.write_text("\n".join(markdown_blocks), encoding="utf-8")

        return {"json": str(json_path), "markdown": str(md_path)}
