"""Field extraction and indicator-specific validation for automatic system approval."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from indicator_rules import rule_for
from kra_catalog import MOBILE_TO_WEB, find_criterion, load_catalog

COUNTABLE_ACCOMPLISHMENT_STATUSES = {"validated", "approved", "system_approved"}

DATE_PATTERN = re.compile(
    r"\b("
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[\s,./-]+\d{1,2}[\s,./-]+\d{4}"
    r"|\d{1,2}[\s,./-]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[\s,./-]+\d{4}"
    r"|\d{4}[\s,./-]\d{1,2}[\s,./-]\d{1,2}"
    r"|\b(20\d{2}|19\d{2})\b"
    r"|(?:AY|SY)\s*[\s./-]*\d{4}\s*[-–]\s*\d{4}"
    r")",
    re.IGNORECASE,
)

AUTHOR_LINE = re.compile(r"(?im)^(?:author(?:s)?|prepared by|submitted by)\s*[:\-]\s*(.+)$")

RATING_PATTERNS = [
    re.compile(r"(?:osetr|osefr|overall(?:\s+set|\s+sef)?\s+rating|rating summary)[:\s]+(\d+(?:\.\d+)?)", re.I),
    re.compile(r"(?:overall|rating|score)[:\s]+(\d+(?:\.\d+)?)\s*(?:%|percent)?", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:rating|score|osetr|osefr)?", re.I),
]

ISSN_PATTERN = re.compile(r"\b\d{4}[- ]?\d{3}[\dxX]\b")
ISBN_PATTERN = re.compile(r"\b(?:ISBN(?:-1[03])?:?\s*)?(?:97[89][- ]?)?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?\d[\dXx]\b")


def extract_fields(*, title: str, author: str | None, ocr_text: str) -> dict:
    cleaned_title = (title or "").strip()
    authors: list[str] = []
    if author and author.strip():
        authors = [part.strip() for part in re.split(r"[;/]| and ", author) if part.strip()]
    if not authors and ocr_text:
        for line in ocr_text.splitlines():
            match = AUTHOR_LINE.search(line.strip())
            if match:
                authors = [
                    part.strip()
                    for part in re.split(r"[;,]| and ", match.group(1))
                    if part.strip()
                ]
                break
    date_value = None
    for source in (ocr_text, title or ""):
        match = DATE_PATTERN.search(source or "")
        if match:
            date_value = match.group(1).strip()
            break
    haystack = " ".join(part for part in (title, author, ocr_text) if part)
    return {
        "title": cleaned_title,
        "authors": authors,
        "date": date_value,
        "issn": ISSN_PATTERN.search(haystack or "") is not None,
        "isbn": ISBN_PATTERN.search(haystack or "") is not None,
        "rating": extract_rating(haystack),
    }


def extract_rating(text: str | None) -> float | None:
    if not text:
        return None
    for pattern in RATING_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if 0 <= value <= 100:
                return value
    return None


def _similar_title(a: str, b: str) -> bool:
    left = (a or "").strip().lower()
    right = (b or "").strip().lower()
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= 0.88


def find_duplicate_accomplishment(
    existing_docs,
    *,
    indicator_id: str | None,
    title: str,
    file_hash: str | None = None,
    exclude_public_id: str | None = None,
) -> str | None:
    if not indicator_id and not file_hash:
        return None
    countable = COUNTABLE_ACCOMPLISHMENT_STATUSES
    for doc in existing_docs or []:
        if exclude_public_id and getattr(doc, "public_id", None) == exclude_public_id:
            continue
        status = getattr(doc, "status", None)
        if status not in countable:
            continue
        if file_hash and getattr(doc, "file_hash", None) == file_hash:
            return getattr(doc, "public_id", None)
        if indicator_id and getattr(doc, "indicator_id", None) == indicator_id:
            if _similar_title(getattr(doc, "title", ""), title):
                return getattr(doc, "public_id", None)
    return None


def authorship_consistent(
    indicator_id: str | None, authors_count: int, contribution_percent
) -> tuple[bool, str | None]:
    rule = rule_for(indicator_id)
    if not rule or authors_count <= 0:
        return True, None
    contribution = rule.get("contribution") or "sole"
    lowered = (indicator_id or "").lower()
    if contribution == "declared" and contribution_percent is None:
        return False, "A declared contribution percentage is required for this indicator."
    if authors_count > 1 and (contribution == "sole" or "-sole" in lowered):
        return False, "Multiple authors were detected for a sole-authorship indicator."
    return True, None


def validate_scoring_inputs(
    indicator_id: str | None,
    *,
    rating: float | None,
    contribution_percent: float | None,
) -> tuple[bool, list[str]]:
    rule = rule_for(indicator_id)
    if not rule:
        return True, []
    reasons: list[str] = []
    if rule.get("multiplier") is not None and rating is None:
        reasons.append("Overall rating is required for this indicator.")
    if (rule.get("contribution") or "") == "declared" and contribution_percent is None:
        reasons.append("Contribution percentage is required for this indicator.")
    return not reasons, reasons


def validate_indicator_fields(
    indicator_id: str | None,
    fields: dict,
    *,
    ocr_text: str,
) -> tuple[bool, list[str]]:
    """Indicator-specific required fields (replaces universal title/author/date for all types)."""
    reasons: list[str] = []
    iid = (indicator_id or "").lower()
    title = fields.get("title")
    authors = fields.get("authors") or []
    date = fields.get("date")
    rating = fields.get("rating")

    if not indicator_id:
        reasons.append("No indicator was identified for field validation.")
        return False, reasons

    if iid in {"kra1-a-student", "kra1-a-supervisor"}:
        if rating is None:
            label = "OSETR" if "student" in iid else "OSEFR"
            reasons.append(f"{label} or overall rating was not found in the document.")
        if not date:
            reasons.append("Academic period or evaluation date is required for this evaluation summary.")
        return not reasons, reasons

    if "journal" in iid or "proceeding" in iid:
        if not title:
            reasons.append("Publication title is required.")
        if not authors:
            reasons.append("Author name is required for publication evidence.")
        if not date:
            reasons.append("Publication date or year is required.")
        if "journal" in iid and not fields.get("issn") and "issn" not in (ocr_text or "").lower():
            reasons.append("Journal evidence should include an ISSN or clear journal identifier.")
        return not reasons, reasons

    if "textbook" in iid or "module" in iid or "manual" in iid:
        if not title:
            reasons.append("Material title is required.")
        if not authors:
            reasons.append("Author or developer name is required.")
        if not date and not fields.get("isbn"):
            reasons.append("Publication year or ISBN is required for instructional materials.")
        return not reasons, reasons

    if "patent" in iid:
        if not title:
            reasons.append("Patent or IP title is required.")
        if "patent" not in (ocr_text or "").lower() and "utility model" not in (ocr_text or "").lower():
            reasons.append("Patent documentation should reference a patent or utility model.")
        return not reasons, reasons

    if "linkage" in iid or "mou" in iid or "extension" in iid:
        if not date:
            reasons.append("Agreement or activity date is required.")
        if not any(
            token in (ocr_text or "").lower()
            for token in ("mou", "moa", "memorandum", "partnership", "extension", "community")
        ):
            reasons.append("Extension or linkage evidence should describe the partnership or activity.")
        return not reasons, reasons

    if any(token in iid for token in ("training", "seminar", "certificate", "award")):
        if not date:
            reasons.append("Date of training, seminar, or award is required.")
        return not reasons, reasons

    # Default documentary evidence
    if not title:
        reasons.append("Document title is required.")
    if not authors:
        reasons.append("Faculty author or subject name is required.")
    if not date:
        reasons.append("Document date or coverage period is required.")
    return not reasons, reasons


def detect_criterion_contradiction(
    *,
    declared_kra: str | None,
    criterion_id: str | None,
    resolved_indicator_id: str | None,
    haystack: str,
) -> str | None:
    """Flag when OCR/title content aligns much more strongly with another criterion under the same KRA."""
    if not declared_kra or not criterion_id or not haystack.strip():
        return None
    from document_classifier import score_indicator_text

    web_kra = MOBILE_TO_WEB.get(declared_kra or "")
    if not web_kra:
        return None
    selected = find_criterion(criterion_id)
    if not selected:
        return None

    best_selected = 0
    if resolved_indicator_id:
        for indicator in selected["criterion"].get("indicators") or []:
            if indicator.get("id") == resolved_indicator_id:
                best_selected, _ = score_indicator_text(indicator, haystack)
                break
    else:
        for indicator in selected["criterion"].get("indicators") or []:
            score, _ = score_indicator_text(indicator, haystack)
            best_selected = max(best_selected, score)

    best_other = 0
    other_label = None
    for kra in load_catalog().get("kras") or []:
        if kra.get("id") != web_kra:
            continue
        for criterion in kra.get("criteria") or []:
            if criterion.get("id") == criterion_id:
                continue
            for indicator in criterion.get("indicators") or []:
                score, _ = score_indicator_text(indicator, haystack)
                if score > best_other:
                    best_other = score
                    other_label = criterion.get("name") or criterion.get("id")
        break

    if best_other >= 5 and best_other >= best_selected + 3:
        return (
            f"The document content fits {other_label} more strongly than the selected criterion "
            f"({best_other} vs {best_selected} keyword score)."
        )
    return None
