from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from story_agent.formatter import InstagramFormatter
from story_agent.models import Citation, ImageAsset, Insight


def sample_insight() -> Insight:
    return Insight(
        category="life_application",
        headline="From Teaching to Tuesday: One Action You Can Take Today",
        story="A short practical discipleship insight.",
        action_step="Take one specific faith action this week.",
        confidence="medium",
        uncertainty_note="Heuristic output; validate full context manually.",
        key_terms=["prayer", "discipleship", "service"],
        citations=[
            Citation(
                doc_id="doc-1",
                title="Sample Source",
                url="https://example.org/source",
                quote="Pray always.",
                verification="high",
            )
        ],
        image=ImageAsset(
            query="family prayer photograph",
            image_url="https://example.org/image.jpg",
            page_url="https://example.org/page",
            title="File:Example.jpg",
            attribution="Example Author",
            license_name="CC BY-SA 4.0",
            is_probably_non_ai=True,
        ),
    )


class InstagramFormatterTests(unittest.TestCase):
    def test_write_creates_instagram_export_bundle(self) -> None:
        formatter = InstagramFormatter()
        insight = sample_insight()
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = formatter.write(output_dir=temp_dir, insights=[insight], warnings=[])

            self.assertIn("instagram_export_dir", paths)
            self.assertIn("instagram_scheduler_json", paths)
            self.assertIn("instagram_hashtag_bank_txt", paths)

            export_dir = Path(paths["instagram_export_dir"])
            scheduler_path = Path(paths["instagram_scheduler_json"])
            hashtag_path = Path(paths["instagram_hashtag_bank_txt"])
            self.assertTrue(export_dir.exists())
            self.assertTrue(scheduler_path.exists())
            self.assertTrue(hashtag_path.exists())

            captions_dir = export_dir / "captions"
            caption_files = list(captions_dir.glob("*.txt"))
            self.assertEqual(len(caption_files), 1)
            caption_text = caption_files[0].read_text(encoding="utf-8")
            self.assertIn("Hashtags:", caption_text)
            self.assertIn("#ldsstudy", caption_text)

            scheduler = json.loads(scheduler_path.read_text(encoding="utf-8"))
            self.assertEqual(scheduler["platform"], "instagram")
            self.assertEqual(scheduler["template"], "square_card_v1")
            self.assertEqual(scheduler["card_count"], 1)
            self.assertEqual(scheduler["cards"][0]["post_type"], "feed_square")
            self.assertEqual(scheduler["cards"][0]["canvas"]["width"], 1080)
            self.assertEqual(scheduler["cards"][0]["canvas"]["height"], 1080)

    def test_write_creates_stable_dev_output_bundle(self) -> None:
        formatter = InstagramFormatter()
        insight = sample_insight()
        with tempfile.TemporaryDirectory() as temp_dir:
            dev_dir = Path(temp_dir) / "development_outputs" / "latest"
            paths = formatter.write(
                output_dir=temp_dir,
                insights=[insight],
                warnings=[],
                dev_output_dir=dev_dir,
            )

            self.assertIn("dev_json", paths)
            self.assertIn("dev_markdown", paths)
            self.assertIn("dev_instagram_export_dir", paths)
            self.assertIn("dev_instagram_scheduler_json", paths)
            self.assertIn("dev_instagram_hashtag_bank_txt", paths)

            self.assertTrue(Path(paths["dev_json"]).exists())
            self.assertTrue(Path(paths["dev_markdown"]).exists())
            self.assertTrue(Path(paths["dev_instagram_scheduler_json"]).exists())
            self.assertTrue(Path(paths["dev_instagram_hashtag_bank_txt"]).exists())

            dev_scheduler = json.loads(
                Path(paths["dev_instagram_scheduler_json"]).read_text(encoding="utf-8")
            )
            self.assertEqual(dev_scheduler["platform"], "instagram")
            self.assertEqual(dev_scheduler["cards"][0]["post_type"], "feed_square")


if __name__ == "__main__":
    unittest.main()
