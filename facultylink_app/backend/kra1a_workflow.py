"""SET/SEF semester records, validation, and Criterion A presentation payload."""

from __future__ import annotations

from uuid import uuid4

from document_validation import verify_identity
from kra1a_evaluation import (
    CRITERION_A_MAX,
    SET_INDICATOR,
    SEF_INDICATOR,
    aggregate_criterion_a,
    aggregate_rating_indicator,
)
from kra1a_record_extraction import extract_semester_records
from kra1a_section10 import required_semesters_for_period, section10_catalog


def _new_record_public_id() -> str:
    return f"evr-{uuid4().hex[:10]}"


def sync_evaluation_records_for_document(
    doc,
    *,
    ocr_text: str,
    uploader_name: str | None,
    fields: dict | None = None,
    indicator_id: str | None = None,
    EvaluationRecord,
    db,
) -> list:
    """Parse OCR text, persist logical semester records, and derive document approval."""
    fields = fields or {}
    extracted = extract_semester_records(
        ocr_text=ocr_text or "",
        title=getattr(doc, "title", "") or "",
        indicator_id=indicator_id or getattr(doc, "indicator_id", None),
        academic_year=fields.get("date"),
        academic_term=fields.get("academic_term"),
        rating=fields.get("rating"),
    )
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    for row in list(getattr(doc, "evaluation_records", []) or []):
        if getattr(row, "deleted_at", None) is None:
            row.deleted_at = now

    kind = "summary" if len(extracted) > 1 else "individual"
    approved = 0
    created = []
    named = fields.get("named_parties") or fields.get("authors") or []
    for item in extracted:
        identity_ok, _label, identity_message = verify_identity(
            item.indicator_id,
            uploader_name=uploader_name,
            named_parties=named,
        )
        valid = bool(identity_ok and item.rating is not None and item.academic_year and item.semester)
        validation_status = "Valid" if valid else "Needs Verification"
        status = "system_approved" if valid else "pendingReview"
        message = identity_message if not identity_ok else ""
        if item.rating is None or item.rating < 0 or item.rating > 100:
            validation_status = "Needs Verification"
            status = "pendingReview"
            message = message or "Rating must be between 0 and 100."
        row = EvaluationRecord(
            public_id=_new_record_public_id(),
            user_id=doc.user_id,
            source_document_id=doc.id,
            indicator_id=item.indicator_id,
            academic_year=item.academic_year,
            semester=item.semester,
            rating=float(item.rating),
            status=status,
            validation_status=validation_status,
            validation_message=message[:500] if message else None,
            source_line=item.source_line,
            page_hint=item.page_hint,
            extraction_kind=kind,
        )
        db.session.add(row)
        created.append(row)
        if status == "system_approved":
            approved += 1

    info = dict(getattr(doc, "extracted_info", None) or {})
    info["Evaluation record count"] = str(len(created))
    info["Evaluation extraction kind"] = kind
    if created:
        info["Evaluation records JSON"] = [
            {
                "indicatorId": r.indicator_id,
                "academicYear": r.academic_year,
                "semester": r.semester,
                "rating": r.rating,
                "status": r.status,
                "validationStatus": r.validation_status,
                "sourceLine": r.source_line,
            }
            for r in created
        ]
    doc.extracted_info = info

    if not created:
        return created
    if approved == len(created):
        doc.status = "system_approved"
        doc.flagged_for_review = False
        doc.validation_result = "System approved after OCR and semester record validation."
    elif approved > 0:
        doc.status = "pendingReview"
        doc.validation_result = "Some semester records need verification."
    return created


def backfill_evaluation_records(user, documents, *, EvaluationRecord, db) -> None:
    """Create evaluation records for legacy Criterion A uploads that predate the records table."""
    from document_validation import extract_fields
    from kra1a_evaluation import RATING_AGGREGATION_INDICATORS

    uploader = user.profile.full_name if user and user.profile else None
    for doc in documents:
        indicator = getattr(doc, "indicator_id", None)
        if getattr(doc, "criterion_id", None) != "kra1-a" and indicator not in RATING_AGGREGATION_INDICATORS:
            continue
        active_rows = [
            row
            for row in (getattr(doc, "evaluation_records", None) or [])
            if getattr(row, "deleted_at", None) is None
        ]
        if active_rows:
            continue
        text = getattr(doc, "extracted_text", None) or ""
        if not text.strip():
            continue
        fields = extract_fields(
            title=getattr(doc, "title", "") or "",
            author=getattr(doc, "author", None),
            ocr_text=text,
            indicator_id=indicator,
        )
        sync_evaluation_records_for_document(
            doc,
            ocr_text=text,
            uploader_name=uploader,
            fields=fields,
            indicator_id=indicator,
            EvaluationRecord=EvaluationRecord,
            db=db,
        )


def collect_active_records(user, EvaluationRecord) -> list:
    return (
        EvaluationRecord.query.filter_by(user_id=user.id)
        .filter(EvaluationRecord.deleted_at.is_(None))
        .filter(EvaluationRecord.status != "invalid")
        .all()
    )


def criterion_a_assessment(user, documents, *, EvaluationRecord) -> dict:
    profile = user.profile if user else None
    exception_code = getattr(profile, "evaluation_period_exception", None) if profile else None
    exception_verified = bool(getattr(profile, "evaluation_period_exception_verified", False)) if profile else False
    records = collect_active_records(user, EvaluationRecord)
    required = required_semesters_for_period(
        exception_code=exception_code,
        exception_verified=exception_verified,
    )

    def _aggregate(indicator_id: str):
        return aggregate_rating_indicator(
            documents,
            indicator_id,
            required_semesters=required,
            exception_verified=exception_verified,
            evaluation_records=records,
        )

    set_result = _aggregate(SET_INDICATOR)
    sef_result = _aggregate(SEF_INDICATOR)
    total = min(float(set_result.get("points") or 0) + float(sef_result.get("points") or 0), CRITERION_A_MAX)
    record_rows = [r.to_dict() for r in records if r.status != "invalid"]
    return {
        "criterionId": "kra1-a",
        "criterionMax": CRITERION_A_MAX,
        "criterionPoints": round(total, 2),
        "set": {
            **set_result,
            "label": "Student Evaluation of Teachers (SET)",
            "weightPercent": 60,
            "records": [r for r in record_rows if r["indicatorId"] == SET_INDICATOR],
        },
        "sef": {
            **sef_result,
            "label": "Supervisor's Evaluation of Faculty (SEF)",
            "weightPercent": 40,
            "records": [r for r in record_rows if r["indicatorId"] == SEF_INDICATOR],
        },
        "section10": {
            "activeException": exception_code,
            "verified": exception_verified,
            "catalog": section10_catalog(),
            "requiredSemesters": required,
        },
    }
