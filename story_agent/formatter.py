from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Insight


class InstagramFormatter:
    """Formats insight objects into short Instagram-style cards."""

    CATEGORY_TAGS = {
        "prophetic_signal": ["prophecywatch", "signsofthetimes", "spiritualdiscernment"],
        "authority_commonality": ["apostolicteachings", "firstpresidency", "quorumofthetwelve"],
        "life_application": ["dailydiscipleship", "faithinaction", "covenantliving"],
        "preparation": ["spiritualpreparedness", "temporalpreparedness", "steadfast"],
        "faith_evidence": ["faithstories", "testimony", "hopeinchrist"],
        "inconclusive": ["studyandpray", "carefuldiscernment"],
    }
    BASE_TAGS = [
        "ldsstudy",
        "churchofjesuschrist",
        "scripturestudy",
        "comefollowme",
        "christcentered",
        "dailyfaith",
        "gospelinsights",
    ]

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

    def to_instagram_caption(self, insight: Insight) -> str:
        hashtags = self._hashtags_for(insight)
        lines = [
            insight.headline,
            "",
            insight.story,
            "",
            f"Action step: {insight.action_step}",
            "",
            f"Confidence: {insight.confidence}",
            f"Uncertainty: {insight.uncertainty_note}",
            "",
            "Sources (verify context before sharing):",
        ]
        for citation in insight.citations[:3]:
            lines.append(f"- {citation.title} | quote check: {citation.verification}")
            lines.append(f"  {citation.url}")
        if insight.image:
            lines.extend(
                [
                    "",
                    "Image credit:",
                    f"- {insight.image.attribution} | {insight.image.license_name}",
                    f"- {insight.image.page_url}",
                ]
            )
        lines.extend(["", "Hashtags:", hashtags])
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

        instagram_paths = self._write_instagram_export(
            output_path=output_path,
            insights=insights,
            timestamp=timestamp,
        )
        return {
            "json": str(json_path),
            "markdown": str(md_path),
            "instagram_export_dir": instagram_paths["instagram_export_dir"],
            "instagram_scheduler_json": instagram_paths["instagram_scheduler_json"],
            "instagram_hashtag_bank_txt": instagram_paths["instagram_hashtag_bank_txt"],
        }

    def _write_instagram_export(
        self,
        output_path: Path,
        insights: list[Insight],
        timestamp: str,
    ) -> dict[str, str]:
        export_dir = output_path / f"instagram_{timestamp}"
        captions_dir = export_dir / "captions"
        captions_dir.mkdir(parents=True, exist_ok=True)

        scheduler_cards: list[dict[str, Any]] = []
        hashtag_bank: set[str] = set()

        for index, insight in enumerate(insights, start=1):
            slug = self._slugify(insight.headline)
            caption_path = captions_dir / f"{index:02d}_{slug}.txt"
            caption_text = self.to_instagram_caption(insight)
            caption_path.write_text(caption_text, encoding="utf-8")

            tags = self._hashtags_for(insight).split(" ")
            hashtag_bank.update(tag for tag in tags if tag.startswith("#"))

            scheduler_cards.append(
                {
                    "post_id": f"{timestamp}-{index:02d}",
                    "publish_order": index,
                    "channel": "instagram",
                    "post_type": "feed_square",
                    "aspect_ratio": "1:1",
                    "canvas": {"width": 1080, "height": 1080},
                    "headline_text": insight.headline,
                    "body_text": insight.story,
                    "cta_text": insight.action_step,
                    "confidence": insight.confidence,
                    "uncertainty_note": insight.uncertainty_note,
                    "caption_file": str(caption_path),
                    "hashtags": [tag.lstrip("#") for tag in tags if tag.startswith("#")],
                    "image": {
                        "image_url": insight.image.image_url if insight.image else None,
                        "page_url": insight.image.page_url if insight.image else None,
                        "attribution": insight.image.attribution if insight.image else None,
                        "license_name": insight.image.license_name if insight.image else None,
                        "is_probably_non_ai": insight.image.is_probably_non_ai if insight.image else False,
                    },
                    "citations": [
                        {
                            "title": citation.title,
                            "url": citation.url,
                            "verification": citation.verification,
                            "quote": citation.quote,
                        }
                        for citation in insight.citations
                    ],
                }
            )

        scheduler_payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "platform": "instagram",
            "template": "square_card_v1",
            "card_count": len(scheduler_cards),
            "cards": scheduler_cards,
        }
        scheduler_path = export_dir / "scheduler_square_cards.json"
        scheduler_path.write_text(
            json.dumps(scheduler_payload, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

        hashtag_path = export_dir / "hashtags_bank.txt"
        hashtag_path.write_text(" ".join(sorted(hashtag_bank)), encoding="utf-8")

        return {
            "instagram_export_dir": str(export_dir),
            "instagram_scheduler_json": str(scheduler_path),
            "instagram_hashtag_bank_txt": str(hashtag_path),
        }

    @staticmethod
    def _slugify(value: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
        return sanitized[:60] or "post"

    def _hashtags_for(self, insight: Insight, max_tags: int = 18) -> str:
        tags: list[str] = []
        tags.extend(self.BASE_TAGS)
        tags.extend(self.CATEGORY_TAGS.get(insight.category, []))
        tags.extend(self._keyword_tags(insight.key_terms))

        deduped: list[str] = []
        seen = set()
        for tag in tags:
            normalized = tag.lower().replace("#", "").strip()
            normalized = re.sub(r"[^a-z0-9_]", "", normalized)
            if not normalized:
                continue
            normalized = normalized[:28]
            marker = f"#{normalized}"
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(marker)
            if len(deduped) >= max_tags:
                break
        return " ".join(deduped)

    @staticmethod
    def _keyword_tags(terms: list[str]) -> list[str]:
        keyword_tags: list[str] = []
        for term in terms:
            compact = re.sub(r"[^a-zA-Z0-9]+", "", term.lower())
            if len(compact) < 4:
                continue
            keyword_tags.append(compact)
        return keyword_tags
