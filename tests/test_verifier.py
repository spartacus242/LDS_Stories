from datetime import datetime, timezone
import unittest

from story_agent.models import Document
from story_agent.verifier import QuoteVerifier


def make_document(content: str) -> Document:
    return Document(
        doc_id="doc-1",
        name="Sample",
        url="https://example.org/doc",
        source_type="scripture",
        content=content,
        title="Sample Document",
        published_at=datetime.now(timezone.utc),
    )


class QuoteVerifierTests(unittest.TestCase):
    def test_exact_match(self) -> None:
        verifier = QuoteVerifier()
        doc = make_document("Faith in Jesus Christ brings hope to the soul.")
        result = verifier.verify("Faith in Jesus Christ brings hope to the soul.", doc)
        self.assertTrue(result.is_exact_match)
        self.assertEqual(result.confidence_label, "high")

    def test_close_match(self) -> None:
        verifier = QuoteVerifier(close_match_threshold=0.75)
        doc = make_document("Faith in Jesus Christ brings hope to the soul.")
        result = verifier.verify("Faith in Christ brings hope to souls.", doc)
        self.assertFalse(result.is_exact_match)
        self.assertTrue(result.is_close_match)
        self.assertEqual(result.confidence_label, "medium")

    def test_inconclusive_low_match(self) -> None:
        verifier = QuoteVerifier()
        doc = make_document("Faith in Jesus Christ brings hope to the soul.")
        result = verifier.verify("Computers are becoming self-aware.", doc)
        self.assertFalse(result.is_exact_match)
        self.assertFalse(result.is_close_match)
        self.assertEqual(result.confidence_label, "low")


if __name__ == "__main__":
    unittest.main()
