"""Per-item Annex A evidence validation for indicator evidence packages."""

from __future__ import annotations

import re
from typing import Any

from indicator_rules import rule_for

RequirementState = str  # missing | uploaded_unverified | system_verified | reviewer_verified | invalid

STATE_MISSING = "missing"
STATE_UPLOADED_UNVERIFIED = "uploaded_unverified"
STATE_SYSTEM_VERIFIED = "system_verified"
STATE_REVIEWER_VERIFIED = "reviewer_verified"
STATE_INVALID = "invalid"


def _slug_requirement(text: str, index: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:48]
    return f"req-{index}-{base or 'item'}"


def requirement_catalog(indicator_id: str | None) -> list[dict]:
    rule = rule_for(indicator_id) or {}
    items = rule.get("evidence") or []
    return [
        {
            "index": idx,
            "id": _slug_requirement(label, idx),
            "label": label,
            "mandatoryHumanVerification": _requires_mandatory_human(label),
        }
        for idx, label in enumerate(items)
    ]


def _requires_mandatory_human(text: str) -> bool:
    lower = (text or "").lower()
    triggers = (
        "ched equivalency",
        "foreign degree",
        "certification from",
        "attesting indexing",
        "research director",
        "when required",
    )
    return any(token in lower for token in triggers)


def _keywords_from_label(label: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{4,}", (label or "").lower())
    stop = {"using", "with", "from", "that", "this", "prescribed", "template", "document", "documents"}
    return [w for w in words if w not in stop][:12]


def _ocr_for_slot(documents: list[Any], requirement_index: int) -> str:
    chunks: list[str] = []
    for doc in documents:
        idx = getattr(doc, "requirement_index", None)
        if idx is None:
            info = getattr(doc, "extracted_info", None) or {}
            if isinstance(info, dict):
                raw = info.get("Evidence requirement index")
                try:
                    idx = int(raw) if raw is not None and str(raw).strip() != "" else None
                except (TypeError, ValueError):
                    idx = None
        if idx is not None and int(idx) != int(requirement_index):
            continue
        text = (getattr(doc, "extracted_text", None) or "").strip()
        if not text:
            info = getattr(doc, "extracted_info", None) or {}
            if isinstance(info, dict):
                text = (info.get("OCR excerpt") or "").strip()
        if text:
            chunks.append(text)
    if not chunks and requirement_index == 0 and documents:
        # Primary file fallback for legacy single-upload rows.
        doc = documents[0]
        text = (getattr(doc, "extracted_text", None) or "").strip()
        if not text:
            info = getattr(doc, "extracted_info", None) or {}
            if isinstance(info, dict):
                text = (info.get("OCR excerpt") or "").strip()
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _assess_requirement(label: str, ocr_text: str, *, fields_ok: bool, identity_ok: bool) -> RequirementState:
    text = (ocr_text or "").strip()
    if not text:
        return STATE_MISSING
    lower = text.lower()
    keywords = _keywords_from_label(label)
    if not keywords:
        return STATE_UPLOADED_UNVERIFIED
    hits = sum(1 for kw in keywords if kw in lower)
    ratio = hits / max(len(keywords), 1)
    if _requires_mandatory_human(label):
        if ratio >= 0.35 and fields_ok and identity_ok:
            return STATE_UPLOADED_UNVERIFIED
        return STATE_MISSING if ratio < 0.2 else STATE_UPLOADED_UNVERIFIED
    if ratio >= 0.5 and fields_ok and identity_ok:
        return STATE_SYSTEM_VERIFIED
    if ratio >= 0.25 or len(text) > 80:
        return STATE_UPLOADED_UNVERIFIED
    return STATE_MISSING


def assess_package_requirements(
    indicator_id: str | None,
    documents: list[Any],
    *,
    fields_ok: bool = True,
    identity_ok: bool = True,
    reviewer_states: dict | None = None,
) -> dict:
    """Return per-requirement states and package-level completeness."""
    catalog = requirement_catalog(indicator_id)
    reviewer_states = reviewer_states or {}
    if not catalog:
        return {
            "requirements": [],
            "allMandatoryMet": True,
            "completeValid": bool(documents) and fields_ok and identity_ok,
            "needsReviewer": False,
            "missingLabels": [],
            "uncertainLabels": [],
        }

    requirements: list[dict] = []
    missing: list[str] = []
    uncertain: list[str] = []
    needs_reviewer = False
    all_met = True

    for item in catalog:
        idx = item["index"]
        rid = item["id"]
        override = reviewer_states.get(rid) or reviewer_states.get(str(idx))
        if override in {STATE_REVIEWER_VERIFIED, STATE_INVALID}:
            state = override
        else:
            ocr = _ocr_for_slot(documents, idx)
            state = _assess_requirement(item["label"], ocr, fields_ok=fields_ok, identity_ok=identity_ok)
        if state in {STATE_SYSTEM_VERIFIED, STATE_REVIEWER_VERIFIED}:
            pass
        elif state == STATE_MISSING:
            missing.append(item["label"])
            all_met = False
        elif state in {STATE_UPLOADED_UNVERIFIED, STATE_INVALID}:
            uncertain.append(item["label"])
            all_met = False
            if state == STATE_UPLOADED_UNVERIFIED and item.get("mandatoryHumanVerification"):
                needs_reviewer = True
        else:
            uncertain.append(item["label"])
            all_met = False
        requirements.append({**item, "state": state})

    complete_valid = all_met and not missing and not uncertain and fields_ok and identity_ok
    if any(item.get("mandatoryHumanVerification") and item["state"] != STATE_REVIEWER_VERIFIED for item in requirements):
        complete_valid = False
        needs_reviewer = True

    return {
        "requirements": requirements,
        "allMandatoryMet": all_met,
        "completeValid": complete_valid,
        "needsReviewer": needs_reviewer,
        "missingLabels": missing,
        "uncertainLabels": uncertain,
    }
