"""Reviewer corrections to OCR-extracted metadata (audit trail + field overrides)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

ALLOWED_OVERRIDE_KEYS = frozenset(
    {
        "facultyName",
        "extractedTitle",
        "extractedDate",
        "academicYear",
        "academicTerm",
        "evaluationRating",
        "documentTitle",
    }
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _parse_rating(value: Any) -> float | None:
    raw = _clean_text(value)
    if not raw:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", raw)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def fields_from_extracted_info(info: dict | None) -> dict:
    info = info or {}
    rating = _parse_rating(info.get("Extracted rating"))
    names = _clean_text(info.get("Extracted names") or info.get("Extracted author(s)"))
    parties = [part.strip() for part in re.split(r"[;/]| and ", names) if part.strip()]
    date = _clean_text(info.get("Extracted date") or info.get("Academic year"))
    title = _clean_text(info.get("Extracted title"))
    name_from_document = _clean_text(info.get("Name source")) == "Document" or bool(parties)
    if _clean_text(info.get("Reviewer verified identity")) == "yes":
        name_from_document = True
    fields: dict = {
        "title": title,
        "date": date,
        "academic_term": _clean_text(info.get("Academic term")),
        "rating": rating,
        "named_parties": parties,
        "authors": parties,
        "name_from_document": name_from_document,
        "identity_label": _clean_text(info.get("Identity field label")) or "Named party",
    }
    return fields


def apply_field_overrides(fields: dict, overrides: dict) -> tuple[dict, list[dict]]:
    """Apply reviewer-supplied values onto the extracted field map."""
    entries: list[dict] = []
    updated = dict(fields)

    def record(field_key: str, label: str, before: str, after: str) -> None:
        if before == after:
            return
        entries.append(
            {
                "field": field_key,
                "label": label,
                "original": before,
                "corrected": after,
            }
        )

    if "facultyName" in overrides:
        before = "; ".join(updated.get("named_parties") or updated.get("authors") or [])
        after = _clean_text(overrides["facultyName"])
        parties = [part.strip() for part in re.split(r"[;/]| and ", after) if part.strip()]
        updated["named_parties"] = parties
        updated["authors"] = parties
        updated["name_from_document"] = bool(parties)
        record("facultyName", "Faculty / named party", before, after)

    title_key = "documentTitle" if "documentTitle" in overrides else "extractedTitle"
    if title_key in overrides:
        before = _clean_text(updated.get("title"))
        after = _clean_text(overrides[title_key])
        updated["title"] = after
        record(title_key, "Document title", before, after)

    if "extractedDate" in overrides:
        before = _clean_text(updated.get("date"))
        after = _clean_text(overrides["extractedDate"])
        updated["date"] = after
        record("extractedDate", "Date / period", before, after)

    if "academicYear" in overrides:
        before = _clean_text(updated.get("date"))
        after = _clean_text(overrides["academicYear"])
        updated["date"] = after
        record("academicYear", "Academic year", before, after)

    if "academicTerm" in overrides:
        before = _clean_text(updated.get("academic_term"))
        after = _clean_text(overrides["academicTerm"])
        updated["academic_term"] = after
        record("academicTerm", "Academic term", before, after)

    if "evaluationRating" in overrides:
        before = "" if updated.get("rating") is None else str(updated.get("rating"))
        parsed = _parse_rating(overrides["evaluationRating"])
        updated["rating"] = parsed
        after = "" if parsed is None else str(parsed)
        record("evaluationRating", "Evaluation rating", before, after)

    return updated, entries


def merge_correction_log(
    prior_info: dict | None,
    *,
    reviewer_id: str,
    reason: str,
    new_entries: list[dict],
) -> tuple[str, dict[str, str]]:
    """Return JSON log text and snapshot keys to store on extracted_info."""
    prior_info = prior_info or {}
    log_raw = prior_info.get("Reviewer correction log") or "[]"
    try:
        log = json.loads(log_raw) if isinstance(log_raw, str) else list(log_raw or [])
    except json.JSONDecodeError:
        log = []
    stamp = datetime.now().isoformat(sep=" ", timespec="seconds")
    for entry in new_entries:
        log.append(
            {
                **entry,
                "reviewerId": reviewer_id,
                "reason": reason,
                "at": stamp,
            }
        )
    extras: dict[str, str] = {}
    if new_entries and not prior_info.get("OCR baseline captured"):
        extras["OCR baseline captured"] = "yes"
        for key in (
            "Extracted names",
            "Extracted author(s)",
            "Extracted title",
            "Extracted date",
            "Academic year",
            "Academic term",
            "Extracted rating",
            "Identity verification",
            "Provisional score",
        ):
            if key in prior_info:
                extras[f"OCR original — {key}"] = str(prior_info[key])
    if new_entries:
        extras["Reviewer verified extraction"] = "yes"
        extras["Last correction reason"] = reason
        extras["Last corrected by"] = reviewer_id
        extras["Last corrected at"] = stamp
    return json.dumps(log, ensure_ascii=False), extras


def build_extracted_updates_from_fields(fields: dict, *, identity_message: str | None) -> dict[str, str]:
    parties = fields.get("named_parties") or fields.get("authors") or []
    joined = "; ".join(parties)
    rating = fields.get("rating")
    return {
        "Extracted title": _clean_text(fields.get("title")),
        "Extracted names": joined,
        "Extracted author(s)": joined,
        "Extracted date": _clean_text(fields.get("date")),
        "Academic year": _clean_text(fields.get("date")),
        "Academic term": _clean_text(fields.get("academic_term")),
        "Extracted rating": "" if rating is None else str(rating),
        "Name source": "Document" if fields.get("name_from_document") else "Reviewer verified",
        "Reviewer verified identity": "yes" if parties else "no",
        "Identity verification": identity_message or "",
    }
