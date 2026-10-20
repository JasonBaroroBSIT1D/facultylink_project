"""Effective rank-simulation scores (system-calculated with optional reviewer override)."""

from __future__ import annotations

import json
from typing import Any

from indicator_rules import rule_for
from kra_config import document_earned_points, indicator_cap
from kra1a_evaluation import (
    RATING_AGGREGATION_INDICATORS,
    SET_INDICATOR,
    SEF_INDICATOR,
    aggregate_rating_indicator,
)
from scoring import score_indicator

SIMULATION_EXCLUDED_STATUSES = frozenset(
    {"invalid", "rejected", "needsRevision", "processing", "pending-review"}
)
REVIEWER_ADJUSTED_STATUSES = frozenset({"validated", "approved"})


def parse_extracted_info(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def simulation_eligible_from_info(info: dict) -> bool:
    flag = (info.get("Simulation eligible") or "").strip().lower()
    if flag == "yes":
        return True
    if flag == "no":
        return False
    return False


def system_calculated_points(doc) -> float | None:
    info = parse_extracted_info(getattr(doc, "extracted_info", None))
    for key in ("System-calculated score", "Provisional score"):
        raw = info.get(key)
        if raw is None or not str(raw).strip():
            continue
        try:
            value = float(str(raw).strip())
        except (TypeError, ValueError):
            continue
        if value >= 0:
            return value
    sim_col = getattr(doc, "simulation_points", None)
    if sim_col is not None:
        try:
            value = float(sim_col)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return None


def _cap_points(score: float, doc, config: dict | None) -> float:
    cap = indicator_cap(config or {}, getattr(doc, "indicator_id", None))
    rule = rule_for(getattr(doc, "indicator_id", None))
    if rule and isinstance(rule.get("maxPoints"), (int, float)):
        rule_cap = float(rule["maxPoints"])
        cap = rule_cap if cap is None else min(cap, rule_cap)
    if cap is not None:
        score = min(score, cap)
    return max(score, 0.0)


def document_effective_simulation_points(doc, config: dict | None = None) -> float | None:
    """Return credited simulation points, or None when no score should be shown or counted."""
    if getattr(doc, "deleted_at", None) is not None:
        return None
    status = (getattr(doc, "status", None) or "").strip()
    info = parse_extracted_info(getattr(doc, "extracted_info", None))
    if status in SIMULATION_EXCLUDED_STATUSES:
        return None
    if info.get("Simulation invalidated") == "yes":
        return None
    indicator_id = getattr(doc, "indicator_id", None)
    if indicator_id in RATING_AGGREGATION_INDICATORS:
        return None

    if status in REVIEWER_ADJUSTED_STATUSES and getattr(doc, "reviewer_score", None) is not None:
        try:
            score = float(doc.reviewer_score)
        except (TypeError, ValueError):
            score = None
        if score is not None:
            return _cap_points(score, doc, config)

    if status == "system_approved":
        earned = document_earned_points(doc, config)
        return earned if earned > 0 else None

    if simulation_eligible_from_info(info):
        system = system_calculated_points(doc)
        if system is not None and system > 0:
            return _cap_points(system, doc, config)
    return None


def compute_simulation_eligibility(
    *,
    criterion_id: str | None,
    classification_reliable: bool,
    resolved_indicator: str | None,
    fields_ok: bool,
    scoring_ok: bool,
    identity_ok: bool,
    duplicate_of: str | None,
    contradiction: str | None,
    ocr_text: str,
    ocr_reliable: bool,
    scored_matched: bool,
    scored_base: float | None,
    scored_flagged: bool,
    points: float,
    package_complete_valid: bool = True,
) -> bool:
    if not package_complete_valid:
        return False
    return bool(
        criterion_id
        and classification_reliable
        and resolved_indicator
        and fields_ok
        and scoring_ok
        and identity_ok
        and duplicate_of is None
        and contradiction is None
        and ocr_text.strip()
        and ocr_reliable
        and scored_matched
        and scored_base is not None
        and not scored_flagged
        and points > 0
    )


def indicator_manual_verification_reason(indicator_id: str | None) -> str | None:
    """Indicators with mandatory human verification items in the evidence checklist."""
    from evidence_validation import requirement_catalog

    if not indicator_id:
        return None
    mandatory = [item["label"] for item in requirement_catalog(indicator_id) if item.get("mandatoryHumanVerification")]
    if mandatory:
        return "Some Annex A evidence items require reviewer verification: " + "; ".join(mandatory[:3])
    return None


def stamp_simulation_metadata(
    extracted: dict,
    *,
    eligible: bool,
    points: float,
    auto_approved: bool,
    awaiting_reviewer: bool,
    ocr_reliable: bool,
    fields_ok: bool,
    scoring_ok: bool,
    identity_ok: bool,
    indicator_id: str | None,
    evidence_attestation_required: bool,
    package_needs_reviewer: bool = False,
) -> None:
    extracted["System-calculated score"] = str(round(points, 2)) if points > 0 else ""
    extracted["Simulation eligible"] = "yes" if eligible else "no"
    extracted["OCR status"] = "Completed" if ocr_reliable else "Needs verification"
    complete = fields_ok and scoring_ok and identity_ok
    extracted["Evidence completeness"] = "Complete" if complete else "Incomplete"
    rating_aggregation = indicator_id in RATING_AGGREGATION_INDICATORS
    if auto_approved and complete:
        extracted["Validation status"] = "Valid"
        extracted["Document approval"] = "System Approved"
    elif not ocr_reliable or not identity_ok:
        extracted["Validation status"] = "Needs Verification"
    elif eligible:
        extracted["Validation status"] = "Valid"
    elif not fields_ok or not scoring_ok:
        extracted["Validation status"] = "Invalid"
    else:
        extracted["Validation status"] = "Needs Verification"
    extracted["Scoring eligibility"] = "Eligible" if eligible else "Not eligible"
    manual = indicator_manual_verification_reason(indicator_id)
    if evidence_attestation_required and not eligible:
        extracted["Human verification required"] = "yes"
    elif manual:
        extracted["Human verification required"] = "conditional"
    else:
        extracted["Human verification required"] = "no"
    if eligible:
        extracted["Scoring status"] = "Automatically Scored"
        extracted["Simulation score source"] = "System-calculated"
        extracted["System validation"] = "System Validated"
        extracted["Processing branch"] = "Complete and valid"
    elif auto_approved and rating_aggregation and complete:
        extracted["Scoring status"] = "Semester verified"
        extracted["Simulation score source"] = "Pending period aggregation"
        extracted["System validation"] = "System Validated"
        extracted["Processing branch"] = "Document valid; indicator aggregation pending"
    elif auto_approved and complete:
        extracted["Scoring status"] = "Automatically Scored"
        extracted["Simulation score source"] = "System-calculated"
        extracted["System validation"] = "System Validated"
        extracted["Processing branch"] = "Complete and valid"
    elif not fields_ok or not scoring_ok:
        extracted["Scoring status"] = "Score unavailable"
        extracted["Simulation score source"] = "Unavailable"
        extracted["Processing branch"] = "Incomplete"
    elif evidence_attestation_required or manual or package_needs_reviewer:
        extracted["Scoring status"] = "Score unavailable"
        extracted["Simulation score source"] = "Unavailable"
        extracted["Processing branch"] = "Needs verification"
    else:
        extracted["Scoring status"] = "Score unavailable"
        extracted["Simulation score source"] = "Unavailable"
        extracted["Processing branch"] = "Requires review"
    if auto_approved:
        extracted["Reviewer oversight status"] = "System confirmed"
    elif eligible:
        extracted["Reviewer oversight status"] = "Awaiting Reviewer Check"
    elif evidence_attestation_required or manual:
        extracted["Reviewer oversight status"] = "Requires Review"
    else:
        extracted["Reviewer oversight status"] = "Awaiting Reviewer Check" if awaiting_reviewer else "Not scored"
    extracted["Verification tier"] = (
        "System approved" if auto_approved else ("Simulation scored" if eligible else "Pending review")
    )


def mark_reviewer_adjusted(info: dict, score: float) -> dict:
    updated = dict(info or {})
    updated["Verified score"] = str(score)
    updated["Simulation score source"] = "Reviewer-adjusted"
    updated["Scoring status"] = "Reviewer-adjusted"
    updated["Reviewer oversight status"] = "Reviewer confirmed"
    updated["Verification tier"] = "Reviewer verified"
    updated["Simulation eligible"] = "yes"
    return updated


def mark_simulation_removed(info: dict, *, reason: str) -> dict:
    updated = dict(info or {})
    updated["Simulation eligible"] = "no"
    updated["Simulation invalidated"] = "yes"
    updated["Scoring status"] = "Score unavailable"
    updated["Simulation score source"] = "Unavailable"
    updated["Reviewer oversight status"] = reason
    updated.pop("Verified score", None)
    return updated


def _rating_from_doc(doc) -> float | None:
    info = parse_extracted_info(getattr(doc, "extracted_info", None))
    raw = info.get("Extracted rating")
    if raw is None or not str(raw).strip():
        return None
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def build_simulation_indicator_entries(
    documents, config: dict | None, *, evaluation_records=None
) -> tuple[list[dict], bool]:
    """Indicator point entries for rank simulation, with SET/SEF six-semester aggregation."""
    includes_pending = False
    best_by_indicator: dict[str, tuple[float, str, Any]] = {}
    active = [doc for doc in documents if getattr(doc, "deleted_at", None) is None]

    for doc in active:
        status = getattr(doc, "status", None) or ""
        if status in {"pendingReview", "pending-review", "processing"}:
            includes_pending = True

    entries: list[dict] = []
    for indicator_id in RATING_AGGREGATION_INDICATORS:
        period = aggregate_rating_indicator(
            active, indicator_id, evaluation_records=evaluation_records
        )
        if period.get("finalized") and float(period.get("points") or 0) > 0:
            entries.append(
                {
                    "indicator_id": indicator_id,
                    "points": float(period["points"]),
                    "semesters": period.get("filledCount"),
                    "averageRating": period.get("averageRating"),
                }
            )
        elif period.get("filledCount"):
            includes_pending = True

    for doc in active:
        indicator_id = getattr(doc, "indicator_id", None) or getattr(doc, "public_id", None)
        if not indicator_id or indicator_id in RATING_AGGREGATION_INDICATORS:
            continue
        earned = document_effective_simulation_points(doc, config)
        if earned is None or earned <= 0:
            continue
        current = best_by_indicator.get(indicator_id)
        kra = getattr(doc, "kra", None)
        if current is None or earned > current[0]:
            best_by_indicator[indicator_id] = (earned, kra, doc)

    for indicator_id, (earned, _kra, _doc) in best_by_indicator.items():
        entries.append({"indicator_id": indicator_id, "points": earned})

    return entries, includes_pending


def stamp_evaluation_period_metadata(documents, *, evaluation_records=None) -> None:
    """Write shared SET/SEF period coverage and simulation score into each member document."""
    for indicator_id, prefix in ((SET_INDICATOR, "SET"), (SEF_INDICATOR, "SEF")):
        period = aggregate_rating_indicator(
            documents, indicator_id, evaluation_records=evaluation_records
        )
        for doc in documents:
            if getattr(doc, "deleted_at", None) is not None:
                continue
            if getattr(doc, "indicator_id", None) != indicator_id:
                continue
            info = dict(parse_extracted_info(getattr(doc, "extracted_info", None)))
            filled = period.get("filledCount") or 0
            required = period.get("requiredSemesters") or 6
            info["Evaluation period filled"] = f"{filled}/{required}"
            info["Evaluation period coverage"] = (
                "Complete" if period.get("coverageComplete") else "Incomplete"
            )
            if period.get("averageRating") is not None:
                info["Evaluation period average"] = str(period["averageRating"])
            if period.get("finalized"):
                info[f"{prefix} period simulation score"] = str(period.get("points") or 0)
                info["Scoring status"] = "Automatically Scored"
                info["Simulation score source"] = "System-calculated"
                info["Simulation eligible"] = "yes"
                info["System-calculated score"] = str(period.get("points") or 0)
                info["Provisional score"] = str(period.get("points") or 0)
                info["Processing branch"] = "Complete and valid"
            else:
                info.pop(f"{prefix} period simulation score", None)
            if period.get("issues"):
                info["Evaluation period issues"] = "; ".join(period["issues"][:4])
            doc.extracted_info = info


def document_simulation_api_fields(doc, config: dict | None = None) -> dict:
    info = parse_extracted_info(getattr(doc, "extracted_info", None))
    indicator_id = getattr(doc, "indicator_id", None)
    effective = document_effective_simulation_points(doc, config)
    period_score = None
    period_label = info.get("Evaluation period filled") or ""
    if indicator_id == SET_INDICATOR:
        raw = info.get("SET period simulation score")
        if raw and str(raw).strip():
            try:
                period_score = float(str(raw).strip())
            except (TypeError, ValueError):
                period_score = None
    elif indicator_id == SEF_INDICATOR:
        raw = info.get("SEF period simulation score")
        if raw and str(raw).strip():
            try:
                period_score = float(str(raw).strip())
            except (TypeError, ValueError):
                period_score = None

    return {
        "effectiveSimulationScore": round(effective, 2) if effective is not None else None,
        "periodSimulationScore": round(period_score, 2) if period_score is not None else None,
        "evaluationPeriodFilled": period_label,
        "systemCalculatedScore": info.get("System-calculated score") or "",
        "simulationScoreSource": info.get("Simulation score source") or "Unavailable",
        "ocrStatus": info.get("OCR status") or "",
        "evidenceCompleteness": info.get("Evidence completeness") or info.get("Completeness status") or "",
        "completenessStatus": info.get("Evidence completeness") or info.get("Completeness status") or "",
        "validationStatus": info.get("Validation status") or "",
        "scoringEligibility": info.get("Scoring eligibility") or "",
        "scoringStatus": info.get("Scoring status") or "",
        "reviewerOversightStatus": info.get("Reviewer oversight status") or "",
        "processingBranch": info.get("Processing branch") or "",
        "simulationEligible": info.get("Simulation eligible") == "yes",
    }


def audit_indicator_catalog() -> list[dict]:
    """Coverage matrix for all configured indicators (all four KRAs)."""
    from indicator_rules import load_indicator_rules, rule_for
    from kra_catalog import find_indicator

    rows: list[dict] = []
    for indicator_id in sorted(load_indicator_rules().keys()):
        found = find_indicator(indicator_id)
        kra_code = found["kra"]["code"] if found else indicator_id.split("-")[0].upper()
        criterion_id = found["criterion"]["id"] if found else ""
        rule = rule_for(indicator_id) or {}
        manual = indicator_manual_verification_reason(indicator_id)
        rows.append(
            {
                "kra": kra_code,
                "criterionId": criterion_id,
                "indicatorId": indicator_id,
                "maxPoints": rule.get("maxPoints"),
                "contribution": rule.get("contribution"),
                "multiplier": rule.get("multiplier"),
                "evidenceCount": len(rule.get("evidence") or []),
                "manualVerification": manual or "",
                "autoScoreWhenComplete": manual is None
                and (rule.get("points") is not None or rule.get("multiplier") is not None),
                "perItemEvidenceValidation": True,
            }
        )
    return rows
