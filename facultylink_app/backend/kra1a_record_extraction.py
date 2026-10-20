"""Extract logical SET/SEF semester records from OCR text (single or consolidated documents)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from document_validation import _normalize_rating_digits, _rating_value, extract_document_period
from kra1a_evaluation import SET_INDICATOR, SEF_INDICATOR

AY_HEADER = re.compile(
    r"(?im)(?:^|\n)\s*(?:academic year|school year|sy|ay)\s*[:\-]?\s*(\d{4}\s*[-–/]\s*\d{4})"
)
AY_INLINE = re.compile(r"(?i)(20\d{2}\s*[-–/]\s*20\d{2})")

SEMESTER_SET_SEF_RATING = re.compile(
    r"(?i)"
    r"(?:(?:1st|first)\s*sem(?:ester)?|(?:2nd|second)\s*sem(?:ester)?|\bsem(?:ester)?\s*([12])\b)"
    r".{0,80}?"
    r"(set|sef|student evaluation|supervisor(?:'?s)?\s*evaluation)"
    r".{0,40}?"
    r"(\d{2,3}(?:\.\d+)?)"
)
SEMESTER_TYPE_RATING = re.compile(
    r"(?i)(1st|first|2nd|second)\s+sem(?:ester)?\s+(set|sef)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)"
)

LINE_SET_RATING = re.compile(
    r"(?i)(?:overall\s+)?(?:set|student evaluation(?:\s+of\s+teachers)?)\s*(?:rating|score)?"
    r"\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)"
)
LINE_SEF_RATING = re.compile(
    r"(?i)(?:overall\s+)?(?:sef|supervisor(?:'?s)?\s*evaluation(?:\s+of\s+faculty)?)\s*(?:rating|score)?"
    r"\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)"
)


@dataclass
class ExtractedSemesterRecord:
    indicator_id: str
    academic_year: str
    semester: str  # "1" or "2"
    rating: float
    source_line: str = ""
    page_hint: str = ""


def _normalize_ay(raw: str) -> str:
    text = (raw or "").strip()
    match = re.search(r"(20\d{2})\s*[-–/]\s*(20\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return text


def _semester_from_fragment(fragment: str) -> str:
    text = (fragment or "").lower()
    if re.search(r"(?:1st|first|\bsem(?:ester)?\s*1\b)", text):
        return "1"
    if re.search(r"(?:2nd|second|\bsem(?:ester)?\s*2\b)", text):
        return "2"
    return ""


def _indicator_from_token(token: str) -> str | None:
    t = (token or "").lower()
    if "supervisor" in t or t == "sef":
        return SEF_INDICATOR
    if "student" in t or t == "set":
        return SET_INDICATOR
    return None


def _records_from_consolidated_lines(text: str) -> list[ExtractedSemesterRecord]:
    records: list[ExtractedSemesterRecord] = []
    current_ay = ""
    for match in AY_HEADER.finditer(text):
        current_ay = _normalize_ay(match.group(1))
    lines = text.splitlines()
    line_ay = current_ay
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        ay_match = AY_INLINE.search(line)
        if ay_match and len(line) < 40:
            line_ay = _normalize_ay(ay_match.group(1))
            continue
        for match in SEMESTER_TYPE_RATING.finditer(line):
            sem = _semester_from_fragment(match.group(1))
            indicator = _indicator_from_token(match.group(2))
            rating = _rating_value(match.group(3))
            ay = line_ay or _normalize_ay(extract_document_period(ocr_text=line, title="") or "")
            if indicator and sem and ay and rating is not None:
                records.append(
                    ExtractedSemesterRecord(
                        indicator_id=indicator,
                        academic_year=ay,
                        semester=sem,
                        rating=rating,
                        source_line=line[:240],
                    )
                )
        for match in SEMESTER_SET_SEF_RATING.finditer(line):
            sem = _semester_from_fragment(match.group(0))
            if not sem:
                sem_digit = match.group(1)
                if sem_digit in {"1", "2"}:
                    sem = sem_digit
            indicator = _indicator_from_token(match.group(2))
            rating = _rating_value(match.group(3))
            ay = line_ay or _normalize_ay(extract_document_period(ocr_text=line, title="") or "")
            if indicator and sem and ay and rating is not None:
                records.append(
                    ExtractedSemesterRecord(
                        indicator_id=indicator,
                        academic_year=ay,
                        semester=sem,
                        rating=rating,
                        source_line=line[:240],
                    )
                )
    return records


def _single_semester_record(
    *,
    text: str,
    title: str,
    indicator_id: str | None,
    academic_year: str | None,
    academic_term: str | None,
    rating: float | None,
) -> list[ExtractedSemesterRecord]:
    if rating is None:
        return []
    ay = _normalize_ay(academic_year or extract_document_period(ocr_text=text, title=title) or "")
    sem = _semester_from_fragment(academic_term or title or "")
    if not indicator_id or not ay or not sem:
        return []
    return [
        ExtractedSemesterRecord(
            indicator_id=indicator_id,
            academic_year=ay,
            semester=sem,
            rating=float(rating),
            source_line=(title or "")[:240],
        )
    ]


def _dedupe_records(records: list[ExtractedSemesterRecord]) -> list[ExtractedSemesterRecord]:
    seen: dict[tuple[str, str, str], ExtractedSemesterRecord] = {}
    for record in records:
        key = (record.indicator_id, record.academic_year, record.semester)
        seen[key] = record
    return list(seen.values())


def extract_semester_records(
    *,
    ocr_text: str,
    title: str = "",
    indicator_id: str | None = None,
    academic_year: str | None = None,
    academic_term: str | None = None,
    rating: float | None = None,
) -> list[ExtractedSemesterRecord]:
    """Return every identifiable SET/SEF semester rating in the document."""
    text = _normalize_rating_digits(ocr_text or "")
    consolidated = _dedupe_records(_records_from_consolidated_lines(text))
    if len(consolidated) >= 2:
        return consolidated
    if len(consolidated) == 1:
        return consolidated

    records: list[ExtractedSemesterRecord] = []
    current_ay = _normalize_ay(
        academic_year or extract_document_period(ocr_text=text, title=title) or ""
    )
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for pattern, iid in ((LINE_SET_RATING, SET_INDICATOR), (LINE_SEF_RATING, SEF_INDICATOR)):
            match = pattern.search(stripped)
            if not match:
                continue
            value = _rating_value(match.group(1))
            if value is None:
                continue
            sem = _semester_from_fragment(stripped) or _semester_from_fragment(title or "")
            ay = current_ay or _normalize_ay(extract_document_period(ocr_text=stripped, title=title) or "")
            use_indicator = iid if indicator_id in (None, iid) else indicator_id
            if indicator_id and indicator_id not in {SET_INDICATOR, SEF_INDICATOR}:
                use_indicator = indicator_id
            if ay and sem:
                records.append(
                    ExtractedSemesterRecord(
                        indicator_id=use_indicator or iid,
                        academic_year=ay,
                        semester=sem,
                        rating=value,
                        source_line=stripped[:240],
                    )
                )
    if records:
        return _dedupe_records(records)

    if indicator_id in {SET_INDICATOR, SEF_INDICATOR}:
        single = _single_semester_record(
            text=text,
            title=title,
            indicator_id=indicator_id,
            academic_year=academic_year,
            academic_term=academic_term,
            rating=rating,
        )
        if single:
            return _dedupe_records(single)
    return []
