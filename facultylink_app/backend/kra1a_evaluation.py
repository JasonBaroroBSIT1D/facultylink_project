"""KRA I Criterion A — SET / SEF evaluation period aggregation (JC No. 01, s. 2026)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SET_INDICATOR = "kra1-a-student"
SEF_INDICATOR = "kra1-a-supervisor"
RATING_AGGREGATION_INDICATORS = frozenset({SET_INDICATOR, SEF_INDICATOR})
SET_MULTIPLIER = 36.0
SEF_MULTIPLIER = 24.0
CRITERION_A_MAX = 60.0

# Standard reclassification window referenced in audit: three academic years, two semesters each.
STANDARD_REQUIRED_SEMESTERS = 6


@dataclass
class EvaluationSlot:
    academic_year: str
    semester: str
    rating: float
    document_id: str
    source: str  # system | reviewer | record
    record_id: str = ""
    extraction_kind: str = "individual"


def _normalize_ay(raw: str) -> str:
    text = (raw or "").strip()
    match = re.search(r"(20\d{2})\s*[-–]\s*(20\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else text


def _normalize_semester(raw: str) -> str:
    text = (raw or "").strip().lower()
    if not text:
        return ""
    if "1" in text or "first" in text:
        return "1"
    if "2" in text or "second" in text:
        return "2"
    return text


def _rating_from_doc(doc: Any) -> float | None:
    if getattr(doc, "reviewer_score", None) is not None and getattr(doc, "status", None) in {
        "validated",
        "approved",
    }:
        try:
            return float(doc.reviewer_score)
        except (TypeError, ValueError):
            pass
    info = getattr(doc, "extracted_info", None) or {}
    if not isinstance(info, dict):
        return None
    raw = info.get("Extracted rating") or info.get("Verified score")
    if raw is None or not str(raw).strip():
        return None
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _infer_semester_from_text(*parts: str) -> str:
    for part in parts:
        text = (part or "").strip().lower()
        if not text:
            continue
        if re.search(r"(?:^|[\s_./-])sem(?:ester)?\s*2\b|2nd\s*sem|\bsecond\s*sem", text):
            return "2"
        if re.search(r"(?:^|[\s_./-])sem(?:ester)?\s*1\b|1st\s*sem|\bfirst\s*sem", text):
            return "1"
    return ""


def _slot_key(doc: Any) -> tuple[str, str] | None:
    info = getattr(doc, "extracted_info", None) or {}
    if not isinstance(info, dict):
        info = {}
    title = getattr(doc, "title", None) or ""
    file_name = getattr(doc, "file_name", None) or ""
    ay = _normalize_ay(
        str(
            info.get("Academic year")
            or info.get("Extracted date")
            or title
            or file_name
            or ""
        )
    )
    sem = _normalize_semester(str(info.get("Academic term") or ""))
    if not sem:
        sem = _infer_semester_from_text(title, file_name, str(info.get("Extracted title") or ""))
    if not ay or not sem:
        return None
    rating = _rating_from_doc(doc)
    if rating is None:
        return None
    return ay, sem


def _record_priority(record) -> int:
    kind = (getattr(record, "extraction_kind", None) or "individual").lower()
    status = (getattr(record, "status", None) or "").lower()
    score = 0
    if status == "system_approved":
        score += 10
    if kind == "individual":
        score += 5
    return score


def _merge_slot(
    by_key: dict[tuple[str, str], EvaluationSlot],
    slot: EvaluationSlot,
    issues: list[str],
) -> None:
    key = (slot.academic_year, slot.semester)
    existing = by_key.get(key)
    if not existing:
        by_key[key] = slot
        return
    issues.append(
        f"Overlapping semester {slot.academic_year} sem {slot.semester}; "
        f"keeping {existing.document_id} over {slot.document_id}."
    )


def collect_evaluation_slots(
    documents: list[Any],
    indicator_id: str,
    *,
    evaluation_records: list[Any] | None = None,
) -> tuple[list[EvaluationSlot], list[str]]:
    """Build semester slots and issue messages (duplicates, out-of-period, missing)."""
    issues: list[str] = []
    by_key: dict[tuple[str, str], EvaluationSlot] = {}
    record_best: dict[tuple[str, str], Any] = {}
    for record in evaluation_records or []:
        if getattr(record, "deleted_at", None) is not None:
            continue
        if getattr(record, "indicator_id", None) != indicator_id:
            continue
        if getattr(record, "status", None) not in {"system_approved", "validated", "approved"}:
            continue
        ay = _normalize_ay(getattr(record, "academic_year", "") or "")
        sem = _normalize_semester(getattr(record, "semester", "") or "")
        if not ay or not sem:
            continue
        key = (ay, sem)
        prev = record_best.get(key)
        if prev is None or _record_priority(record) >= _record_priority(prev):
            record_best[key] = record
    for record in record_best.values():
        doc_ref = getattr(record, "source_document", None)
        doc_id = getattr(doc_ref, "public_id", "") if doc_ref else ""
        ay = _normalize_ay(getattr(record, "academic_year", "") or "")
        sem = _normalize_semester(getattr(record, "semester", "") or "")
        slot = EvaluationSlot(
            ay,
            sem,
            float(record.rating),
            doc_id,
            "record",
            record_id=getattr(record, "public_id", "") or "",
            extraction_kind=getattr(record, "extraction_kind", None) or "individual",
        )
        _merge_slot(by_key, slot, issues)

    covered_docs = {
        getattr(getattr(r, "source_document", None), "public_id", None)
        for r in (evaluation_records or [])
        if getattr(r, "deleted_at", None) is None
    }
    for doc in documents:
        if getattr(doc, "deleted_at", None) is not None:
            continue
        if getattr(doc, "indicator_id", None) != indicator_id:
            continue
        if getattr(doc, "public_id", None) in covered_docs and evaluation_records:
            continue
        info = getattr(doc, "extracted_info", None) or {}
        if isinstance(info, dict) and info.get("Simulation invalidated") == "yes":
            continue
        key_parts = _slot_key(doc)
        if not key_parts:
            issues.append(f"{getattr(doc, 'public_id', 'doc')}: missing academic year, semester, or rating.")
            continue
        ay, sem = key_parts
        rating = _rating_from_doc(doc)
        if rating is None:
            continue
        source = "reviewer" if getattr(doc, "reviewer_score", None) is not None else "system"
        slot = EvaluationSlot(ay, sem, rating, getattr(doc, "public_id", ""), source)
        _merge_slot(by_key, slot, issues)
    return list(by_key.values()), issues


def aggregate_rating_indicator(
    documents: list[Any],
    indicator_id: str,
    *,
    required_semesters: int = STANDARD_REQUIRED_SEMESTERS,
    exception_verified: bool = False,
    evaluation_records: list[Any] | None = None,
) -> dict:
    slots, issues = collect_evaluation_slots(
        documents, indicator_id, evaluation_records=evaluation_records
    )
    multiplier = SET_MULTIPLIER if indicator_id == SET_INDICATOR else SEF_MULTIPLIER
    filled = len(slots)
    coverage_complete = filled >= required_semesters or (exception_verified and filled > 0)
    if not slots:
        return {
            "indicatorId": indicator_id,
            "slots": [],
            "filledCount": 0,
            "requiredSemesters": required_semesters,
            "coverageComplete": False,
            "averageRating": None,
            "points": 0.0,
            "maxPoints": multiplier,
            "issues": issues or ["No evaluation ratings in period."],
            "finalized": False,
        }
    if not coverage_complete:
        issues.append(
            f"Incomplete evaluation-period coverage: {filled} of {required_semesters} required semesters present."
        )
        return {
            "indicatorId": indicator_id,
            "slots": [slot.__dict__ for slot in slots],
            "filledCount": filled,
            "requiredSemesters": required_semesters,
            "coverageComplete": False,
            "averageRating": None,
            "points": 0.0,
            "maxPoints": multiplier,
            "issues": issues,
            "finalized": False,
        }
    avg = sum(s.rating for s in slots) / len(slots)
    points = round((avg / 100.0) * multiplier, 2)
    points = min(points, multiplier)
    return {
        "indicatorId": indicator_id,
        "slots": [slot.__dict__ for slot in slots],
        "filledCount": filled,
        "requiredSemesters": required_semesters,
        "coverageComplete": True,
        "averageRating": round(avg, 2),
        "points": points,
        "maxPoints": multiplier,
        "issues": issues,
        "finalized": True,
    }


def aggregate_criterion_a(
    documents: list[Any],
    *,
    exception_verified: bool = False,
    evaluation_records: list[Any] | None = None,
    required_semesters: int = STANDARD_REQUIRED_SEMESTERS,
) -> dict:
    set_result = aggregate_rating_indicator(
        documents,
        SET_INDICATOR,
        exception_verified=exception_verified,
        evaluation_records=evaluation_records,
        required_semesters=required_semesters,
    )
    sef_result = aggregate_rating_indicator(
        documents,
        SEF_INDICATOR,
        exception_verified=exception_verified,
        evaluation_records=evaluation_records,
        required_semesters=required_semesters,
    )
    total = min(
        float(set_result.get("points") or 0) + float(sef_result.get("points") or 0),
        CRITERION_A_MAX,
    )
    return {"set": set_result, "sef": sef_result, "criterionPoints": round(total, 2), "criterionMax": CRITERION_A_MAX}
