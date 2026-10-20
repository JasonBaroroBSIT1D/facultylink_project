"""Evidence package lifecycle and evaluation."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from evidence_validation import assess_package_requirements
from kra1a_evaluation import SET_INDICATOR, SEF_INDICATOR, aggregate_rating_indicator
from kra_config import load_active_kra_config
from scoring import process_upload


def new_package_public_id() -> str:
    return f"pkg-{uuid4().hex[:10]}"


def active_package_documents(package) -> list[Any]:
    return [
        doc
        for doc in (getattr(package, "documents", None) or [])
        if getattr(doc, "deleted_at", None) is None
    ]


def evaluate_package(
    package,
    documents: list[Any],
    *,
    config: dict | None,
    uploader_name: str | None,
    existing_docs=None,
) -> dict:
    """Recompute requirement checklist and simulation eligibility for a package."""
    indicator_id = getattr(package, "indicator_id", None)
    active_docs = [d for d in documents if getattr(d, "deleted_at", None) is None]
    if not active_docs:
        return {
            "completeValid": False,
            "simulationEligible": False,
            "points": 0.0,
            "assessment": {},
            "processed": {},
            "checklistJson": "[]",
        }

    primary = sorted(active_docs, key=lambda d: int(getattr(d, "requirement_index", 0) or 0))[0]
    processed = process_upload(
        title=getattr(primary, "title", "") or "Evidence",
        author=getattr(primary, "author", None),
        file_path=getattr(primary, "file_path", None),
        declared_kra=getattr(package, "kra", None) or getattr(primary, "kra", None),
        criterion_id=getattr(package, "criterion_id", None) or getattr(primary, "criterion_id", None),
        indicator_id=indicator_id or getattr(primary, "indicator_id", None),
        config=config,
        existing_docs=existing_docs or [],
        uploader_name=uploader_name,
        stored_ocr_text=getattr(primary, "extracted_text", None),
        prior_extracted_info=getattr(primary, "extracted_info", None) or {},
        force_manual_review=True,
        package_evidence_documents=active_docs,
    )

    reviewer_states = getattr(package, "reviewer_requirement_states", None) or {}
    if isinstance(reviewer_states, str):
        try:
            reviewer_states = json.loads(reviewer_states)
        except (TypeError, ValueError):
            reviewer_states = {}

    assessment = assess_package_requirements(
        indicator_id,
        active_docs,
        fields_ok=processed.get("_fields_ok", True),
        identity_ok=processed.get("_identity_ok", True),
        reviewer_states=reviewer_states if isinstance(reviewer_states, dict) else {},
    )

    points = float(processed.get("exact_points") or processed.get("points") or 0)
    simulation_eligible = bool(assessment.get("completeValid") and points > 0)

    if indicator_id in {SET_INDICATOR, SEF_INDICATOR}:
        exception = getattr(package, "evaluation_exception_verified", False)
        period = aggregate_rating_indicator(
            active_docs,
            indicator_id,
            exception_verified=bool(exception),
        )
        assessment["evaluationPeriod"] = period
        if period.get("finalized"):
            points = float(period.get("points") or 0)
            simulation_eligible = points > 0
        else:
            simulation_eligible = False
            points = 0.0

    checklist_json = json.dumps(assessment.get("requirements") or [])
    return {
        "assessment": assessment,
        "processed": processed,
        "simulationEligible": simulation_eligible,
        "points": points,
        "checklistJson": checklist_json,
        "completeValid": assessment.get("completeValid"),
    }


def stamp_documents_from_package_eval(documents: list[Any], eval_result: dict, package_public_id: str) -> None:
    assessment = eval_result.get("assessment") or {}
    processed = eval_result.get("processed") or {}
    info_base = dict(processed.get("extracted_info") or {})
    for doc in documents:
        if getattr(doc, "deleted_at", None) is not None:
            continue
        info = dict(getattr(doc, "extracted_info", None) or info_base)
        info["Evidence package"] = package_public_id
        info["Evidence checklist"] = eval_result.get("checklistJson") or "[]"
        info["Package completeness"] = "Complete" if assessment.get("completeValid") else "Incomplete"
        if assessment.get("missingLabels"):
            info["Missing evidence items"] = "; ".join(assessment["missingLabels"])
        if assessment.get("uncertainLabels"):
            info["Uncertain evidence items"] = "; ".join(assessment["uncertainLabels"])
        period = assessment.get("evaluationPeriod")
        if period:
            info["Evaluation period coverage"] = (
                "Complete" if period.get("coverageComplete") else "Incomplete"
            )
            if period.get("averageRating") is not None:
                info["Evaluation period average"] = str(period["averageRating"])
            if period.get("issues"):
                info["Evaluation period issues"] = "; ".join(period["issues"][:5])
        info["Simulation eligible"] = "yes" if eval_result.get("simulationEligible") else "no"
        info["System-calculated score"] = str(round(float(eval_result.get("points") or 0), 2))
        if eval_result.get("simulationEligible"):
            info["Scoring status"] = "Automatically Scored"
            info["Simulation score source"] = "System-calculated"
            info["Processing branch"] = "Complete and valid"
        else:
            info["Scoring status"] = "Score unavailable"
            info["Simulation score source"] = "Unavailable"
            info["Processing branch"] = (
                "Needs verification" if assessment.get("needsReviewer") else "Incomplete"
            )
        doc.extracted_info = info
        doc.simulation_points = (
            int(round(float(eval_result.get("points") or 0)))
            if eval_result.get("simulationEligible")
            else 0
        )


def re_evaluate_and_persist(package, *, db, Document, user, existing_docs=None) -> dict:
    """Run package evaluation and persist checklist + simulation fields on package and member docs."""
    config = load_active_kra_config(db)
    uploader_name = user.profile.full_name if getattr(user, "profile", None) else None
    docs = active_package_documents(package)
    eval_result = evaluate_package(
        package,
        docs,
        config=config,
        uploader_name=uploader_name,
        existing_docs=existing_docs,
    )
    package.checklist_json = eval_result.get("checklistJson") or "[]"
    package.simulation_eligible = bool(eval_result.get("simulationEligible"))
    package.simulation_points = float(eval_result.get("points") or 0)
    stamp_documents_from_package_eval(docs, eval_result, package.public_id)
    return eval_result
