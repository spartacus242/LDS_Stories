from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import Citation, Document, Insight
from .text_utils import extract_keywords, split_sentences, trim_to_word_count
from .verifier import QuoteVerifier


PROPHECY_TERMS = {
    "warn",
    "warning",
    "prepare",
    "coming",
    "last",
    "days",
    "tribulation",
    "calamity",
    "gather",
    "watch",
    "signs",
    "covenant",
}

EVENT_TERMS = {
    "war",
    "famine",
    "earthquake",
    "pandemic",
    "inflation",
    "poverty",
    "migration",
    "displacement",
    "conflict",
    "technology",
    "ai",
    "surveillance",
    "instability",
    "violence",
}

ACTION_TERMS = {
    "pray": "Set aside 10 minutes daily for prayer with a specific question in mind.",
    "repent": "Identify one habit to correct this week and act on it today.",
    "serve": "Do one anonymous act of service in the next 48 hours.",
    "study": "Study a focused scripture block and write one action from it.",
    "temple": "Schedule your next temple attendance or family-history task now.",
    "covenant": "Review your covenant path milestones and choose the next step.",
    "minister": "Reach out to one person who may need encouragement today.",
    "fast": "Plan a meaningful fast with a clear spiritual purpose.",
}

TESTIMONY_TERMS = {
    "i testify",
    "i know",
    "witness",
    "miracle",
    "blessing",
    "faith",
    "redeemer",
    "savior",
}

DOCTRINE_TYPES = {
    "scripture",
    "general_authority_talk",
    "doctrine",
    "church_news",
    "historical_church_record",
}

EVENT_TYPES = {
    "current_event",
    "historical_world_event",
    "societal_trend",
    "tech_advance",
}

COMMONALITY_STOPWORDS = {
    "lord",
    "god",
    "all",
    "one",
    "shall",
    "unto",
    "will",
    "can",
    "may",
    "thee",
    "thou",
    "thy",
    "ye",
    "also",
    "jesus",
    "christ",
}

UNSUITABLE_EVENT_TERMS = {
    "epstein",
    "sexual",
    "assault",
    "porn",
    "murder",
    "homicide",
    "execution",
    "kidnap",
    "abuse",
}


@dataclass(slots=True)
class InsightBuilder:
    verifier: QuoteVerifier

    def build(self, documents: list[Document], max_insights: int = 5) -> list[Insight]:
        doctrine_docs = [doc for doc in documents if doc.source_type in DOCTRINE_TYPES]
        event_docs = [doc for doc in documents if doc.source_type in EVENT_TYPES]

        insights: list[Insight] = []
        insights.extend(self._build_prophetic_signals(doctrine_docs, event_docs))
        insights.extend(self._build_authority_commonalities(doctrine_docs))
        insights.extend(self._build_life_application(doctrine_docs, event_docs))
        insights.extend(self._build_preparation(doctrine_docs, event_docs))
        insights.extend(self._build_faith_evidence(doctrine_docs, event_docs))

        if not insights:
            return [
                Insight(
                    category="inconclusive",
                    headline="No Strong Cross-Source Signal Yet",
                    story=(
                        "The current source set did not produce a reliable "
                        "cross-document insight. More sources, better metadata, "
                        "or manual review may be required."
                    ),
                    action_step="Add more official sources and rerun the agent.",
                    confidence="low",
                    uncertainty_note=(
                        "Data is inconclusive. Avoid treating this as a definitive claim."
                    ),
                    key_terms=["inconclusive", "review"],
                    citations=[],
                )
            ]

        deduped: list[Insight] = []
        seen = set()
        for insight in insights:
            marker = (insight.category, insight.headline.lower())
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(insight)
            if len(deduped) >= max_insights:
                break
        return deduped

    def _build_prophetic_signals(self, doctrine_docs: list[Document], event_docs: list[Document]) -> list[Insight]:
        best_candidate: tuple[int, str, Document, str, Document] | None = None

        for doctrine_doc in doctrine_docs:
            for doctrine_sentence in split_sentences(doctrine_doc.content):
                doctrine_terms = set(extract_keywords(doctrine_sentence, limit=8))
                if not doctrine_terms.intersection(PROPHECY_TERMS):
                    continue
                for event_doc in event_docs:
                    for event_sentence in split_sentences(event_doc.content):
                        event_terms = set(extract_keywords(event_sentence, limit=10))
                        if not event_terms.intersection(EVENT_TERMS):
                            continue
                        overlap = doctrine_terms.intersection(event_terms)
                        if len(overlap) < 1:
                            continue
                        score = len(overlap)
                        if not best_candidate or score > best_candidate[0]:
                            best_candidate = (
                                score,
                                ", ".join(sorted(overlap)),
                                doctrine_doc,
                                doctrine_sentence,
                                event_doc,
                            )

        if not best_candidate:
            return []

        _, overlap_text, doctrine_doc, doctrine_quote, event_doc = best_candidate
        event_quote = self._best_sentence_for_terms(
            event_doc,
            overlap_text.split(", "),
            avoid_terms=UNSUITABLE_EVENT_TERMS,
        )
        doctrine_citation = self._citation_for(doctrine_doc, doctrine_quote)
        event_citation = self._citation_for(event_doc, event_quote)

        confidence = "medium"
        uncertainty = (
            "This indicates possible alignment in themes, not proof of a fulfilled prophecy."
        )
        if doctrine_citation.verification == "high" and event_citation.verification in {"high", "medium"}:
            confidence = "medium"

        return [
            Insight(
                category="prophetic_signal",
                headline="Prophetic Pattern Watch: Themes Now in the Headlines",
                story=(
                    "A doctrinal warning and a current event source share themes "
                    f"around {overlap_text}. This can be a useful study signal, "
                    "but it is not conclusive on its own."
                ),
                action_step="Study the cited warning in context, then pray about your personal preparation.",
                confidence=confidence,
                uncertainty_note=uncertainty,
                key_terms=[term.strip() for term in overlap_text.split(",") if term.strip()],
                citations=[doctrine_citation, event_citation],
            )
        ]

    def _build_authority_commonalities(self, doctrine_docs: list[Document]) -> list[Insight]:
        authority_docs = [
            doc
            for doc in doctrine_docs
            if doc.authority_office
            and (
                "quorum of the twelve" in doc.authority_office.lower()
                or "first presidency" in doc.authority_office.lower()
            )
        ]
        if len(authority_docs) < 2:
            return []

        term_to_docs: dict[str, set[str]] = defaultdict(set)
        for doc in authority_docs:
            terms = extract_keywords(
                doc.content,
                limit=30,
                extra_stopwords=COMMONALITY_STOPWORDS,
            )
            for term in terms:
                term_to_docs[term].add(doc.doc_id)

        shared = [(term, len(doc_ids)) for term, doc_ids in term_to_docs.items() if len(doc_ids) >= 2]
        if not shared:
            return []

        shared.sort(key=lambda pair: pair[1], reverse=True)
        top_terms = [term for term, _ in shared[:5]]
        citations: list[Citation] = []

        for doc in authority_docs[:3]:
            sentence = self._best_sentence_for_terms(doc, top_terms)
            if sentence:
                citations.append(self._citation_for(doc, sentence))

        return [
            Insight(
                category="authority_commonality",
                headline=f"Shared Message from Apostolic Voices: {', '.join(top_terms[:3]).title()}",
                story=(
                    "Across recent talks from the First Presidency and/or Quorum of the Twelve, "
                    f"the strongest repeated themes include {', '.join(top_terms)}."
                ),
                action_step="Pick one shared theme and turn it into a family or personal goal this week.",
                confidence="medium",
                uncertainty_note=(
                    "Theme overlap is heuristic and may miss nuance; read full talks for context."
                ),
                key_terms=top_terms,
                citations=citations,
            )
        ]

    def _build_life_application(self, doctrine_docs: list[Document], event_docs: list[Document]) -> list[Insight]:
        candidate_sentence = ""
        candidate_doc: Document | None = None
        matched_action = ""
        prioritized_docs = sorted(
            doctrine_docs,
            key=lambda doc: 0 if doc.source_type == "general_authority_talk" else 1,
        )
        for doc in prioritized_docs:
            for sentence in split_sentences(doc.content):
                sentence_terms = set(extract_keywords(sentence, limit=10))
                for action_term in ACTION_TERMS:
                    if action_term in sentence_terms:
                        candidate_doc = doc
                        candidate_sentence = sentence
                        matched_action = action_term
                        break
                if candidate_doc:
                    break
            if candidate_doc:
                break

        if not candidate_doc:
            return []

        context_terms = extract_keywords(candidate_sentence, limit=6)
        event_sentence = ""
        event_doc_ref: Document | None = None
        for doc in event_docs:
            sentence = self._best_sentence_for_terms(
                doc,
                context_terms,
                avoid_terms=UNSUITABLE_EVENT_TERMS,
            )
            if sentence:
                event_sentence = sentence
                event_doc_ref = doc
                break

        citations = [self._citation_for(candidate_doc, candidate_sentence)]
        if event_doc_ref and event_sentence:
            citations.append(self._citation_for(event_doc_ref, event_sentence))

        return [
            Insight(
                category="life_application",
                headline="From Teaching to Tuesday: One Action You Can Take Today",
                story=(
                    "A repeated doctrinal pattern points to practical discipleship: "
                    f"{trim_to_word_count(candidate_sentence, 20)}"
                ),
                action_step=ACTION_TERMS.get(
                    matched_action,
                    "Choose one doctrine-backed action and schedule it in your calendar today.",
                ),
                confidence="medium",
                uncertainty_note=(
                    "Application guidance is a suggested interpretation and should be personalized."
                ),
                key_terms=context_terms,
                citations=citations,
            )
        ]

    def _build_preparation(self, doctrine_docs: list[Document], event_docs: list[Document]) -> list[Insight]:
        prep_sentences: list[tuple[Document, str]] = []
        for doc in doctrine_docs:
            for sentence in split_sentences(doc.content):
                terms = set(extract_keywords(sentence, limit=10))
                if {"prepare", "watch", "covenant"}.intersection(terms):
                    prep_sentences.append((doc, sentence))

        if not prep_sentences:
            return []

        doctrine_doc, doctrine_sentence = prep_sentences[0]
        event_sentence = ""
        event_doc_ref: Document | None = None
        for doc in event_docs:
            sentence = self._best_sentence_for_terms(
                doc,
                extract_keywords(doctrine_sentence, limit=8),
                avoid_terms=UNSUITABLE_EVENT_TERMS,
            )
            if sentence:
                event_sentence = sentence
                event_doc_ref = doc
                break

        citations = [self._citation_for(doctrine_doc, doctrine_sentence)]
        if event_doc_ref and event_sentence:
            citations.append(self._citation_for(event_doc_ref, event_sentence))

        return [
            Insight(
                category="preparation",
                headline="Prepare, Do Not Panic: A Calm Read of the Times",
                story=(
                    "Preparation teachings emphasize covenant focus, spiritual steadiness, and practical readiness. "
                    "This framing helps respond to uncertainty with faith rather than fear."
                ),
                action_step=(
                    "Create a 3-part plan: spiritual (prayer/scripture), relational (family contact), "
                    "and temporal (basic emergency readiness)."
                ),
                confidence="medium",
                uncertainty_note=(
                    "Current-event linkage can be suggestive but not definitive; avoid sensational conclusions."
                ),
                key_terms=extract_keywords(doctrine_sentence, limit=6),
                citations=citations,
            )
        ]

    def _build_faith_evidence(self, doctrine_docs: list[Document], event_docs: list[Document]) -> list[Insight]:
        testimony_quote = ""
        testimony_doc: Document | None = None
        for doc in doctrine_docs:
            for sentence in split_sentences(doc.content):
                lower_sentence = sentence.lower()
                if any(term in lower_sentence for term in TESTIMONY_TERMS):
                    testimony_quote = sentence
                    testimony_doc = doc
                    break
            if testimony_doc:
                break

        if not testimony_doc:
            return []

        supporting_event_quote = ""
        supporting_event_doc: Document | None = None
        for doc in event_docs:
            sentence = self._best_sentence_for_terms(
                doc,
                extract_keywords(testimony_quote, limit=8),
                avoid_terms=UNSUITABLE_EVENT_TERMS,
            )
            if sentence:
                supporting_event_quote = sentence
                supporting_event_doc = doc
                break

        citations = [self._citation_for(testimony_doc, testimony_quote)]
        if supporting_event_doc and supporting_event_quote:
            citations.append(self._citation_for(supporting_event_doc, supporting_event_quote))

        return [
            Insight(
                category="faith_evidence",
                headline="Faith Under Pressure: Witnesses That Still Matter",
                story=(
                    "Testimony-rich teachings remain relevant when world conditions feel unstable. "
                    "The evidence here is experiential and scriptural, not purely statistical."
                ),
                action_step="Record one personal evidence of God's help from the past month and share it with someone.",
                confidence="medium",
                uncertainty_note=(
                    "Faith evidence includes spiritual interpretation; others may read the same data differently."
                ),
                key_terms=extract_keywords(testimony_quote, limit=6),
                citations=citations,
            )
        ]

    def _best_sentence_for_terms(
        self,
        doc: Document,
        terms: list[str],
        avoid_terms: set[str] | None = None,
    ) -> str:
        if not terms:
            return ""
        best_sentence = ""
        best_score = 0
        term_set = set(terms)
        for sentence in split_sentences(doc.content):
            if avoid_terms and any(term in sentence.lower() for term in avoid_terms):
                continue
            sentence_terms = set(extract_keywords(sentence, limit=12))
            score = len(term_set.intersection(sentence_terms))
            if score > best_score:
                best_sentence = sentence
                best_score = score
        return best_sentence

    def _citation_for(self, doc: Document, quote: str) -> Citation:
        result = self.verifier.verify(quote, doc)
        return Citation(
            doc_id=doc.doc_id,
            title=doc.title or doc.name,
            url=doc.url,
            quote=trim_to_word_count(quote, 45),
            verification=result.confidence_label,
        )
