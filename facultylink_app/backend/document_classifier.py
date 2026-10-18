"""Classify uploaded evidence to an Annex I indicator within a faculty-selected criterion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from kra_catalog import find_criterion, find_indicator

STOP_WORDS = {
    "and",
    "for",
    "the",
    "with",
    "from",
    "per",
    "each",
    "year",
    "years",
    "other",
    "than",
    "into",
    "through",
    "under",
    "over",
    "more",
    "less",
    "not",
    "are",
    "was",
    "has",
    "have",
    "been",
    "may",
    "can",
    "all",
    "any",
    "one",
    "two",
    "three",
    "four",
    "five",
    "points",
    "point",
    "maximum",
    "base",
    "score",
    "faculty",
    "member",
    "members",
    "development",
    "professional",
    "work",
    "creative",
    "innovation",
    "research",
    "instruction",
    "extension",
}

# Extra phrases aligned with DBM–CHED documentary evidence types (not KRA-only keyword rules).
INDICATOR_SIGNALS: dict[str, tuple[str, ...]] = {
    "journal": ("journal", "issn", "peer-reviewed", "peer reviewed", "doi", "abstract", "volume", "issue"),
    "proceeding": ("proceeding", "conference", "symposium", "isbn"),
    "textbook": ("textbook", "isbn", "chapter", "pages"),
    "module": ("module", "learning module", "instructional material"),
    "patent": ("patent", "intellectual property", "utility model"),
    "citation": ("citation", "cited", "scopus", "wos", "web of science"),
    "poetry": ("poem", "poetry", "verse"),
    "essay": ("essay", "narrative"),
    "linkage": ("mou", "memorandum", "partnership", "linkage", "moa"),
    "training": ("training", "seminar", "workshop", "certificate", "tesda", "ched"),
    "award": ("award", "recognition", "plaque", "medal"),
    "admin": ("designation", "coordinator", "chairperson", "dean", "director"),
    "student": ("student evaluation", "student rating", "learner evaluation"),
}

# Indicator-specific phrases (DBM–CHED evidence types) layered on generated keywords.
INDICATOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kra1-a-student": (
        "set",
        "student evaluation of teachers",
        "osetr",
        "fedaf",
        "overall set rating",
        "evaluation rating summary",
    ),
    "kra1-a-supervisor": (
        "sef",
        "supervisor evaluation",
        "osefr",
        "supervisor's evaluation",
        "evaluation of faculty",
    ),
    "kra2-a-journal-sole": ("sole author", "journal article", "peer-reviewed", "issn", "doi"),
    "kra2-a-journal-co": ("co-author", "journal article", "peer-reviewed", "issn"),
    "kra2-a-proceeding-sole": ("conference proceeding", "proceedings", "symposium"),
    "kra2-a-proceeding-co": ("conference proceeding", "co-author", "symposium"),
    "kra2-b-patent": ("patent", "utility model", "intellectual property office"),
    "kra3-a-linkage": ("memorandum of agreement", "moa", "mou", "linkage", "partnership"),
}


@dataclass
class ClassificationResult:
    indicator_id: str | None
    indicator_name: str | None
    confidence: float
    reliable: bool
    reasons: list[str]
    candidates: list[dict]


def _tokenize_indicator(indicator: dict) -> list[str]:
    words: set[str] = set()
    iid = (indicator.get("id") or "").lower()
    for part in iid.split("-"):
        if len(part) > 2 and part not in {"kra1", "kra2", "kra3", "kra4"}:
            if part.isalpha() and len(part) == 1:
                continue
            words.add(part)
    name = (indicator.get("name") or "").lower()
    for token in re.findall(r"[a-z0-9]+", name):
        if len(token) > 2 and token not in STOP_WORDS:
            words.add(token)
    for key, phrases in INDICATOR_SIGNALS.items():
        if key in iid or key in name:
            words.update(phrases)
    words.update(INDICATOR_KEYWORDS.get(indicator.get("id") or "", ()))
    return sorted(words)


@lru_cache(maxsize=256)
def _keywords_for_indicator(indicator_id: str) -> tuple[str, ...]:
    found = find_indicator(indicator_id)
    if not found:
        return ()
    return tuple(_tokenize_indicator(found["indicator"]))


def score_indicator_text(indicator: dict, haystack: str) -> tuple[int, list[str]]:
    if not haystack:
        return 0, []
    text = haystack.lower()
    hits: list[str] = []
    score = 0
    for keyword in _tokenize_indicator(indicator):
        if keyword in text:
            score += min(2, text.count(keyword))
            hits.append(keyword)
    return score, hits


def _authorship_pair_adjustment(
    ranked: list[tuple[int, dict, list[str]]],
    authors_count: int,
) -> list[tuple[int, dict, list[str]]]:
    """Prefer sole vs co-author indicators when scores otherwise tie on document type."""
    if not ranked or authors_count <= 0:
        return ranked
    adjusted: list[tuple[int, dict, list[str]]] = []
    for score, indicator, hits in ranked:
        iid = (indicator.get("id") or "").lower()
        bonus = 0
        if authors_count == 1 and "-co" in iid:
            bonus -= 3
        elif authors_count == 1 and "-sole" in iid:
            bonus += 2
        elif authors_count > 1 and "-sole" in iid:
            bonus -= 3
        elif authors_count > 1 and "-co" in iid:
            bonus += 2
        adjusted.append((score + bonus, indicator, hits))
    adjusted.sort(key=lambda item: item[0], reverse=True)
    return adjusted


def classify_within_criterion(
    criterion_id: str | None,
    *,
    title: str,
    author: str | None,
    ocr_text: str,
    authors_count: int = 1,
) -> ClassificationResult:
    reasons: list[str] = []
    if not criterion_id:
        return ClassificationResult(None, None, 0.0, False, ["No criterion was selected."], [])

    found = find_criterion(criterion_id)
    if not found:
        return ClassificationResult(None, None, 0.0, False, ["The selected criterion was not found."], [])

    haystack = " ".join(part for part in (title, author, ocr_text) if part).strip()
    if not haystack:
        return ClassificationResult(None, None, 0.0, False, ["No text was available for classification."], [])

    indicators = found["criterion"].get("indicators") or []
    if not indicators:
        return ClassificationResult(None, None, 0.0, False, ["This criterion has no indicators configured."], [])

    ranked: list[tuple[int, dict, list[str]]] = []
    for indicator in indicators:
        score, hits = score_indicator_text(indicator, haystack)
        if score > 0:
            ranked.append((score, indicator, hits))
    ranked.sort(key=lambda item: item[0], reverse=True)
    ranked = _authorship_pair_adjustment(ranked, authors_count)

    candidates = [
        {
            "indicatorId": item[1].get("id"),
            "name": item[1].get("name"),
            "score": item[0],
            "keywords": item[2][:8],
        }
        for item in ranked[:5]
    ]

    if not ranked:
        reasons.append("No indicator within the selected criterion matched the extracted text.")
        return ClassificationResult(None, None, 0.0, False, reasons, candidates)

    best_score, best, best_hits = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0
    margin = best_score - second_score
    confidence = round(best_score / (best_score + second_score + 3), 3)

    reliable = (
        best_score >= 3
        and margin >= 2
        and (second_score == 0 or best_score >= second_score * 1.6)
        and bool(ocr_text.strip())
    )

    if not ocr_text.strip():
        reasons.append("OCR did not extract readable text, so indicator classification is not reliable.")
        reliable = False
    elif best_score < 3:
        reasons.append("Indicator keyword evidence is too weak for automatic classification.")
        reliable = False
    elif margin < 2 or (second_score > 0 and best_score < second_score * 1.6):
        reasons.append("More than one indicator within the criterion matched; classification is ambiguous.")
        reliable = False

    if reliable:
        reasons.append(
            f"Classified as {best.get('name')} using OCR text and DBM–CHED indicator rules "
            f"(matched: {', '.join(best_hits[:6])})."
        )
    else:
        reasons.append(
            f"Best match is {best.get('name')}, but automatic approval requires a clearer indicator match."
        )

    return ClassificationResult(
        indicator_id=best.get("id"),
        indicator_name=best.get("name"),
        confidence=confidence,
        reliable=reliable,
        reasons=reasons,
        candidates=candidates,
    )
