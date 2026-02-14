from __future__ import annotations

from difflib import SequenceMatcher

from .models import Document, QuoteVerificationResult
from .text_utils import normalize_for_match, split_sentences, trim_to_word_count


class QuoteVerifier:
    """Checks if a quote can be verified against a source document."""

    def __init__(self, close_match_threshold: float = 0.84):
        self.close_match_threshold = close_match_threshold

    def verify(self, quote: str, document: Document) -> QuoteVerificationResult:
        normalized_quote = normalize_for_match(quote)
        normalized_doc = normalize_for_match(document.content)

        if not normalized_quote:
            return QuoteVerificationResult(
                quote=quote,
                doc_id=document.doc_id,
                is_exact_match=False,
                is_close_match=False,
                best_snippet="",
                score=0.0,
                notes="Quote text was empty after normalization.",
            )

        if normalized_quote in normalized_doc:
            return QuoteVerificationResult(
                quote=quote,
                doc_id=document.doc_id,
                is_exact_match=True,
                is_close_match=True,
                best_snippet=trim_to_word_count(quote, 45),
                score=1.0,
                notes="Exact normalized match found in source text.",
            )

        best_sentence = ""
        best_score = 0.0

        for sentence in split_sentences(document.content):
            normalized_sentence = normalize_for_match(sentence)
            if not normalized_sentence:
                continue
            score = SequenceMatcher(a=normalized_quote, b=normalized_sentence).ratio()
            if score > best_score:
                best_score = score
                best_sentence = sentence

        is_close = best_score >= self.close_match_threshold
        if is_close:
            notes = (
                "Close match found, but the quote is not exact. "
                "Treat as potentially paraphrased and re-check manually."
            )
        else:
            notes = (
                "No strong textual match found. Data may be inconclusive, "
                "source could differ, or quote may be inaccurate."
            )

        return QuoteVerificationResult(
            quote=quote,
            doc_id=document.doc_id,
            is_exact_match=False,
            is_close_match=is_close,
            best_snippet=trim_to_word_count(best_sentence, 55),
            score=round(best_score, 3),
            notes=notes,
        )
