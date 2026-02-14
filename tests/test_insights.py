from datetime import datetime, timezone
import unittest

from story_agent.insights import InsightBuilder
from story_agent.models import Document
from story_agent.verifier import QuoteVerifier


def make_doc(
    doc_id: str,
    source_type: str,
    content: str,
    author: str | None = None,
    authority_office: str | None = None,
) -> Document:
    return Document(
        doc_id=doc_id,
        name=doc_id,
        url=f"https://example.org/{doc_id}",
        source_type=source_type,
        content=content,
        title=doc_id,
        author=author,
        authority_office=authority_office,
        published_at=datetime.now(timezone.utc),
    )


class InsightBuilderTests(unittest.TestCase):
    def test_builder_generates_multiple_insight_types(self) -> None:
        doctrine_1 = make_doc(
            "d1",
            "general_authority_talk",
            (
                "We are warned to prepare in the last days. "
                "I testify that prayer and covenant discipleship bring peace."
            ),
            author="Leader One",
            authority_office="First Presidency",
        )
        doctrine_2 = make_doc(
            "d2",
            "general_authority_talk",
            (
                "As members of the Church we should prepare and watch. "
                "We invite all to pray, serve, and keep covenants."
            ),
            author="Leader Two",
            authority_office="Quorum of the Twelve",
        )
        event_doc = make_doc(
            "e1",
            "current_event",
            (
                "Global conflict and displacement have increased in several regions. "
                "Leaders warn about instability and technology disruption."
            ),
        )

        builder = InsightBuilder(verifier=QuoteVerifier())
        insights = builder.build([doctrine_1, doctrine_2, event_doc], max_insights=5)

        self.assertGreaterEqual(len(insights), 2)
        self.assertTrue(any(insight.citations for insight in insights))

    def test_builder_returns_inconclusive_when_empty(self) -> None:
        builder = InsightBuilder(verifier=QuoteVerifier())
        insights = builder.build([], max_insights=5)
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].category, "inconclusive")


if __name__ == "__main__":
    unittest.main()
