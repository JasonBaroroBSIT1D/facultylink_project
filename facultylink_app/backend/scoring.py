import hashlib
import re
from pathlib import Path
from typing import Any

from indicator_rules import rule_for
from kra_config import (
    DEFAULT_KRA_MAX,
    SCORING_FORMULA,
    WEIGHTED_FORMULA,
    credited_kra_totals,
    document_earned_points,
    final_score,
    load_active_kra_config,
    weighted_final_score,
    weights_for_rank,
)
from ocr import extract_document

VERIFIED_STATUSES = {"validated", "approved", "system_approved"}
PROVISIONAL_STATUSES = {"pendingReview", "pending-review", "processing"}
PROTECTED_DOC_STATUSES = frozenset({"validated", "approved", "needsRevision", "invalid", "rejected"})
RECONCILABLE_STATUSES = frozenset({"pendingReview", "processing", "pending-review"})

# Fallback targets when kra_settings is unavailable (JC No. 01, s. 2026 maxima).
KRA_TARGETS = dict(DEFAULT_KRA_MAX)

KRA_BASE_POINTS = {
    "instruction": 8,
    "research": 10,
    "extension": 8,
    "professionalDevelopment": 5,
}

CLASSIFICATION_RULES = [
    ("research", 1, ("journal", "issn", "publication", "article", "research")),
    ("instruction", 2, ("teaching", "course", "instruction", "syllabus", "classroom")),
    ("extension", 3, ("community", "outreach", "extension", "barangay", "literacy")),
    (
        "professionalDevelopment",
        4,
        ("training", "seminar", "certificate", "tesda", "ched"),
    ),
]


def file_hash(file_path: str | None) -> str | None:
    if not file_path or not Path(file_path).exists():
        return None
    digest = hashlib.sha256()
    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def author_count(author: str | None) -> int:
    if not author or not author.strip():
        return 1
    parts = [part.strip() for part in re.split(r"[;,/&]| and ", author) if part.strip()]
    return max(len(parts), 1)


def classify_kra(text: str, fallback: str | None = None) -> tuple[str, bool]:
    haystack = (text or "").lower()
    matches = []
    for kra, priority, keywords in CLASSIFICATION_RULES:
        if any(keyword in haystack for keyword in keywords):
            matches.append((priority, kra))
    if not matches:
        return fallback or "instruction", False
    matches.sort()
    return matches[0][1], len(matches) > 1


def _as_eval_document(doc, *, fallback_indicator: str | None = None):
    info = getattr(doc, "extracted_info", None) or {}
    if not isinstance(info, dict):
        info = {}
    return type(
        "_EvalDoc",
        (),
        {
            "indicator_id": getattr(doc, "indicator_id", None) or fallback_indicator,
            "deleted_at": getattr(doc, "deleted_at", None),
            "extracted_info": info,
            "reviewer_score": getattr(doc, "reviewer_score", None),
            "status": getattr(doc, "status", None) or "pendingReview",
            "public_id": getattr(doc, "public_id", "") or "",
            "title": getattr(doc, "title", None) or "",
            "file_name": getattr(doc, "file_name", None) or "",
        },
    )()


def _evaluation_period_pool(
    resolved_indicator: str,
    *,
    package_docs,
    context_docs,
    current_slot_info: dict | None,
    current_public_id: str = "",
):
    """Merge package members and same-indicator uploads for SET/SEF period aggregation."""
    from kra1a_evaluation import RATING_AGGREGATION_INDICATORS

    if resolved_indicator not in RATING_AGGREGATION_INDICATORS:
        return []
    pool: dict[str, Any] = {}
    for doc in list(context_docs or []) + list(package_docs or []):
        if getattr(doc, "deleted_at", None) is not None:
            continue
        iid = getattr(doc, "indicator_id", None)
        if iid and iid != resolved_indicator:
            continue
        pid = getattr(doc, "public_id", None) or id(doc)
        pool[str(pid)] = _as_eval_document(doc, fallback_indicator=resolved_indicator)
    if current_slot_info:
        key = current_public_id or "__current__"
        merged = dict(current_slot_info)
        if key in pool:
            existing = pool[key].extracted_info
            merged = {**existing, **merged}
        pool[key] = type(
            "_EvalDoc",
            (),
            {
                "indicator_id": resolved_indicator,
                "deleted_at": None,
                "extracted_info": merged,
                "reviewer_score": None,
                "status": "pendingReview",
                "public_id": current_public_id or "",
                "title": merged.get("Extracted title") or "",
                "file_name": "",
            },
        )()
    return list(pool.values())


def contribution_score(base_points: float, authors: int) -> float:
    """Provisional equal-share estimate using the shared web formula."""
    if authors <= 0:
        authors = 1
    percent = round(100.0 / authors, 2)
    return final_score(base_points, percent)


def score_indicator(
    indicator_id: str | None,
    *,
    contribution_percent: float | None,
    rating: float | None,
    authors: int,
    config: dict | None = None,
) -> dict:
    """Apply the indicator's base points, declared share, and cap."""
    rule = rule_for(indicator_id)
    published = {}
    if config and indicator_id:
        entry = (config.get("indicators") or {}).get(indicator_id) or {}
        if isinstance(entry, dict):
            published = entry
    if not rule and not published:
        return {
            "matched": False,
            "base_points": None,
            "contribution_percent": None,
            "points": 0,
            "max_points": None,
            "flagged": True,
            "note": "No Joint Circular indicator was matched, so a reviewer must assign the score.",
        }

    contribution = (rule or {}).get("contribution") or "sole"
    max_points = (rule or {}).get("maxPoints")
    if isinstance(published.get("maxPoints"), (int, float)):
        max_points = float(published["maxPoints"])

    base = None
    multiplier = (rule or {}).get("multiplier")
    if isinstance(published.get("multiplier"), (int, float)):
        multiplier = float(published["multiplier"])
    if multiplier is not None:
        if rating is None:
            return {
                "matched": True,
                "base_points": None,
                "contribution_percent": None,
                "points": 0,
                "max_points": max_points,
                "flagged": True,
                "note": "A rating from 0 to 100 is required before this indicator can be scored.",
            }
        bounded = min(max(float(rating), 0.0), 100.0)
        base = round((bounded / 100.0) * float(multiplier), 2)
    elif isinstance(published.get("points"), (int, float)):
        base = float(published["points"])
    elif rule and rule.get("points") is not None:
        base = float(rule["points"])

    if base is None:
        return {
            "matched": bool(rule or published),
            "base_points": None,
            "contribution_percent": None,
            "points": 0,
            "max_points": max_points,
            "flagged": True,
            "note": "This indicator has no configured base points.",
        }

    share_note = ""
    if contribution == "declared":
        if contribution_percent is None:
            percent = round(100.0 / max(authors, 1), 2)
            share_note = " No contribution percentage was declared, so an equal author share was used provisionally."
        else:
            percent = min(max(float(contribution_percent), 0.0), 100.0)
    else:
        percent = 100.0

    earned = final_score(base, percent)
    if max_points is not None:
        earned = min(earned, float(max_points))
    return {
        "matched": True,
        "base_points": base,
        "contribution_percent": percent,
        "points": earned,
        "max_points": max_points,
        "flagged": bool(share_note) or contribution == "declared" and contribution_percent is None,
        "note": f"Provisional score uses the Joint Circular indicator.{share_note}",
    }


def process_upload(
    *,
    title: str,
    author: str | None,
    file_path: str | None,
    declared_kra: str | None,
    criterion_id: str | None = None,
    indicator_id: str | None = None,
    contribution_percent: float | None = None,
    rating: float | None = None,
    config: dict | None = None,
    existing_docs=None,
    uploader_name: str | None = None,
    stored_ocr_text: str | None = None,
    field_overrides: dict | None = None,
    prior_extracted_info: dict | None = None,
    reviewer_correction: dict | None = None,
    force_manual_review: bool = False,
    package_evidence_documents=None,
    evaluation_context_documents=None,
    current_public_id: str = "",
):
    from document_classifier import classify_within_criterion
    from document_validation import (
        authorship_consistent,
        detect_criterion_contradiction,
        extract_fields,
        find_duplicate_accomplishment,
        validate_indicator_fields,
        validate_scoring_inputs,
        verify_identity,
    )
    from indicator_identity import resolve_identity_profile
    from kra_catalog import find_indicator

    if stored_ocr_text is not None:
        text = stored_ocr_text or ""
        extraction = type(
            "StoredExtraction",
            (),
            {
                "text": text,
                "reliable": bool(text.strip()),
                "source": "stored",
                "confidence_label": "Stored text",
                "note": "",
            },
        )()
    else:
        extraction = extract_document(file_path)
        text = extraction.text
    combined = " ".join(part for part in (title, author, text) if part)
    kra, ambiguous = classify_kra(combined, declared_kra)
    provisional_authors = author_count(author)
    classification = classify_within_criterion(
        criterion_id,
        title=title,
        author=author,
        ocr_text=text,
        authors_count=provisional_authors,
    )
    resolved_indicator = indicator_id or classification.indicator_id
    fields = extract_fields(
        title=title,
        author=author,
        ocr_text=text,
        indicator_id=resolved_indicator,
    )
    correction_entries: list[dict] = []
    if field_overrides:
        from reviewer_metadata import apply_field_overrides

        fields, correction_entries = apply_field_overrides(fields, field_overrides)
    authors = max(len(fields.get("named_parties") or fields.get("authors") or []), author_count(author))
    indicator_meta = find_indicator(resolved_indicator)
    if indicator_meta and declared_kra and indicator_meta.get("mobileKey") != declared_kra:
        classification.reliable = False
        classification.reasons.append("The identified indicator does not belong to the selected KRA.")

    extracted_rating = fields.get("rating")
    effective_rating = rating if rating is not None else extracted_rating

    scored = score_indicator(
        resolved_indicator,
        contribution_percent=contribution_percent,
        rating=effective_rating,
        authors=authors,
        config=config,
    )
    rule = rule_for(resolved_indicator)
    if scored["matched"] and scored["base_points"] is not None:
        base = scored["base_points"]
        percent = scored["contribution_percent"] or 100.0
        points = scored["points"]
    elif rule and rule.get("multiplier") is not None:
        # SET/SEF and other rating multipliers — never substitute generic KRA fallback points.
        base = scored.get("base_points")
        percent = scored.get("contribution_percent") or 100.0
        points = scored.get("points") or 0
    else:
        # All four KRAs: use indicator configuration only — no generic KRA base-point fallback.
        base = scored.get("base_points")
        percent = scored.get("contribution_percent")
        if percent is None:
            percent = round(100.0 / max(authors, 1), 2)
        points = float(scored.get("points") or 0)

    review_reasons: list[str] = list(classification.reasons)
    if resolved_indicator and points <= 0 and scored.get("note"):
        review_reasons.append(scored["note"])
    fields_ok, field_reasons = validate_indicator_fields(
        resolved_indicator, fields, ocr_text=text
    )
    review_reasons.extend(field_reasons)

    scoring_ok, scoring_reasons = validate_scoring_inputs(
        resolved_indicator,
        rating=effective_rating,
        contribution_percent=contribution_percent,
    )
    review_reasons.extend(scoring_reasons)

    auth_ok, auth_reason = authorship_consistent(
        resolved_indicator, authors, contribution_percent
    )
    if not auth_ok and auth_reason:
        review_reasons.append(auth_reason)

    # The logged-in faculty member comes from the authenticated profile, not the upload form.
    identity_name = (uploader_name or "").strip() or None
    identity_ok, identity_label, identity_message = verify_identity(
        resolved_indicator,
        uploader_name=identity_name,
        named_parties=fields.get("named_parties") or fields.get("authors") or [],
    )
    if not identity_ok:
        review_reasons.append(identity_message)

    file_digest = file_hash(file_path)
    duplicate_of = find_duplicate_accomplishment(
        existing_docs,
        indicator_id=resolved_indicator,
        title=title,
        file_hash=file_digest,
        exclude_public_id=current_public_id or None,
    )
    if duplicate_of:
        review_reasons.append(
            f"Potential duplicate of document {duplicate_of} (same file or accomplishment)."
        )

    contradiction = detect_criterion_contradiction(
        declared_kra=declared_kra,
        criterion_id=criterion_id,
        resolved_indicator_id=resolved_indicator,
        haystack=combined,
    )
    if contradiction:
        review_reasons.append(contradiction)

    if ambiguous:
        review_reasons.append("Extracted text matches more than one auxiliary KRA keyword rule.")
    if not text.strip():
        review_reasons.append(extraction.note or "OCR did not extract readable text from the file.")
    elif not extraction.reliable:
        review_reasons.append(extraction.note or "OCR quality is too low for automatic approval.")

    identity_profile = resolve_identity_profile(resolved_indicator)
    if resolved_indicator and (
        identity_profile.require_named_party or identity_profile.uploader_must_match
    ):
        if not fields.get("name_from_document"):
            review_reasons.append("The identity name was not read from the document text.")
            identity_ok = False

    from evidence_validation import assess_package_requirements

    prior_info = prior_extracted_info if isinstance(prior_extracted_info, dict) else {}
    reviewer_req_states = prior_info.get("Reviewer requirement states")
    if isinstance(reviewer_req_states, str):
        try:
            import json as _json

            reviewer_req_states = _json.loads(reviewer_req_states)
        except (TypeError, ValueError):
            reviewer_req_states = {}
    if not isinstance(reviewer_req_states, dict):
        reviewer_req_states = {}

    package_docs = list(package_evidence_documents or [])
    if not package_docs:
        package_docs = [
            type(
                "_UploadDoc",
                (),
                {
                    "extracted_text": text,
                    "extracted_info": prior_info,
                    "requirement_index": prior_info.get("Evidence requirement index"),
                    "deleted_at": None,
                },
            )()
        ]
    evidence_assessment = assess_package_requirements(
        resolved_indicator,
        package_docs,
        fields_ok=fields_ok,
        identity_ok=identity_ok,
        reviewer_states=reviewer_req_states,
    )
    evidence_reason = None
    if resolved_indicator and (evidence_assessment.get("requirements") or []):
        if not evidence_assessment.get("completeValid"):
            missing = evidence_assessment.get("missingLabels") or []
            uncertain = evidence_assessment.get("uncertainLabels") or []
            if missing:
                evidence_reason = (
                    "Required supporting evidence is missing: " + "; ".join(missing[:4])
                    + ("…" if len(missing) > 4 else "")
                )
            elif uncertain:
                evidence_reason = (
                    "Supporting evidence needs verification: " + "; ".join(uncertain[:4])
                    + ("…" if len(uncertain) > 4 else "")
                )
            else:
                evidence_reason = "Supporting evidence checklist is not complete and valid."
            review_reasons.append(evidence_reason)

    package_complete = bool(evidence_assessment.get("completeValid"))

    from kra1a_evaluation import RATING_AGGREGATION_INDICATORS

    is_rating_aggregation = resolved_indicator in RATING_AGGREGATION_INDICATORS
    classification_ok = classification.reliable or (
        is_rating_aggregation
        and bool(resolved_indicator)
        and (indicator_id or classification.indicator_id == resolved_indicator)
        and fields_ok
        and effective_rating is not None
    )

    auto_approve = (
        bool(criterion_id)
        and classification_ok
        and bool(resolved_indicator)
        and fields_ok
        and scoring_ok
        and auth_ok
        and identity_ok
        and package_complete
        and duplicate_of is None
        and contradiction is None
        and text.strip()
        and extraction.reliable
        and scored["matched"]
        and (scored["base_points"] is not None or (is_rating_aggregation and effective_rating is not None))
        and not scored.get("flagged")
        and not force_manual_review
        and not field_overrides
    )

    from simulation_scoring import compute_simulation_eligibility, stamp_simulation_metadata

    simulation_eligible = compute_simulation_eligibility(
        criterion_id=criterion_id,
        classification_reliable=classification.reliable,
        resolved_indicator=resolved_indicator,
        fields_ok=fields_ok,
        scoring_ok=scoring_ok,
        identity_ok=identity_ok,
        duplicate_of=duplicate_of,
        contradiction=contradiction,
        ocr_text=text,
        ocr_reliable=extraction.reliable,
        scored_matched=bool(scored["matched"]),
        scored_base=scored.get("base_points"),
        scored_flagged=bool(scored.get("flagged")),
        points=float(points or 0),
        package_complete_valid=package_complete,
    )

    evaluation_period = None
    from kra1a_evaluation import SET_INDICATOR, SEF_INDICATOR, aggregate_rating_indicator

    aggregated_indicator_points: float | None = None
    if resolved_indicator in {SET_INDICATOR, SEF_INDICATOR}:
        eval_info = {
            "Academic year": fields.get("date") or "",
            "Academic term": fields.get("academic_term") or "",
            "Extracted rating": str(effective_rating) if effective_rating is not None else "",
            "Extracted title": fields.get("title") or title,
        }
        eval_docs = _evaluation_period_pool(
            resolved_indicator,
            package_docs=package_docs,
            context_docs=evaluation_context_documents,
            current_slot_info=eval_info,
            current_public_id=current_public_id,
        )
        if eval_docs:
            evaluation_period = aggregate_rating_indicator(eval_docs, resolved_indicator)
            if evaluation_period.get("finalized"):
                aggregated_indicator_points = float(evaluation_period.get("points") or 0)
                simulation_eligible = bool(simulation_eligible and aggregated_indicator_points > 0)
            else:
                simulation_eligible = False

    status = "system_approved" if auto_approve else "pendingReview"
    if not identity_ok:
        mismatch = identity_message or "The document identity does not match the logged-in faculty member."
        review_reasons = [mismatch] + [reason for reason in review_reasons if reason != mismatch]
    primary_reason = review_reasons[0] if review_reasons else "Reviewer validation required."
    validation = (
        "System approved after OCR, indicator classification, and field validation."
        if auto_approve
        else primary_reason
    )
    if len(validation) > 250:
        validation = validation[:247] + "..."

    if is_rating_aggregation:
        provisional_display = (
            float(aggregated_indicator_points)
            if aggregated_indicator_points is not None
            else 0.0
        )
        credited_points = 0
    else:
        provisional_display = float(points or 0)
        credited_points = int(round(points)) if auto_approve else 0

    extracted = {
        "Document type": indicator_meta["indicator"]["name"]
        if indicator_meta
        else "Uploaded documentary evidence",
        "Assigned KRA": declared_kra or kra,
        "Detected KRA": kra,
        "Criterion": criterion_id or "",
        "Automatically identified indicator": classification.indicator_name or "",
        "Identified indicator ID": resolved_indicator or "",
        "Classification confidence": str(classification.confidence),
        "Author count": str(authors),
        "Extracted title": fields.get("title") or "",
        "Identity field label": fields.get("identity_label") or identity_label,
        "Identity mode": fields.get("identity_mode") or "",
        "Extracted names": "; ".join(fields.get("named_parties") or fields.get("authors") or []),
        "Extracted author(s)": "; ".join(fields.get("named_parties") or fields.get("authors") or []),
        "Identity verification": identity_message,
        "Name source": "Document" if fields.get("name_from_document") else "Not read from the document",
        "OCR source": extraction.source,
        "OCR confidence": extraction.confidence_label,
        "OCR quality": "Reliable" if extraction.reliable else "Unreliable",
        "OCR note": extraction.note,
        "Extracted date": fields.get("date") or "",
        "Academic year": fields.get("date") or "",
        "Academic term": fields.get("academic_term") or "",
        "Evaluation type": fields.get("evaluation_type") or "",
        "Extracted rating": str(effective_rating) if effective_rating is not None else "",
        "Base points": str(base),
        "Contribution percent": str(percent),
        "Scoring formula": SCORING_FORMULA,
        "Provisional score": str(provisional_display),
        "Contribution score": str(provisional_display),
    }
    if classification.candidates:
        extracted["Classification candidates"] = ", ".join(
            f"{item['name']} ({item['score']})" for item in classification.candidates[:3]
        )
    if text.strip():
        extracted["OCR excerpt"] = text.strip()[:2000]
    else:
        extracted["OCR"] = (
            "Tesseract was not available or the file had no readable text. "
            "Automatic approval requires OCR extraction."
        )
    if scored.get("note"):
        extracted["Scoring note"] = scored["note"]
    if review_reasons and not auto_approve:
        extracted["Review reasons"] = "; ".join(dict.fromkeys(review_reasons))
    import json as _json

    extracted["Evidence checklist"] = _json.dumps(evidence_assessment.get("requirements") or [])
    if evidence_assessment.get("missingLabels"):
        extracted["Missing evidence items"] = "; ".join(evidence_assessment["missingLabels"])
    if evidence_assessment.get("uncertainLabels"):
        extracted["Uncertain evidence items"] = "; ".join(evidence_assessment["uncertainLabels"])
    extracted["Package completeness"] = "Complete" if package_complete else "Incomplete"
    if evaluation_period:
        filled = evaluation_period.get("filledCount") or 0
        required = evaluation_period.get("requiredSemesters") or 6
        extracted["Evaluation period filled"] = f"{filled}/{required}"
        extracted["Evaluation period coverage"] = (
            "Complete" if evaluation_period.get("coverageComplete") else "Incomplete"
        )
        if evaluation_period.get("averageRating") is not None:
            extracted["Evaluation period average"] = str(evaluation_period["averageRating"])
        if evaluation_period.get("finalized"):
            prefix = "SET" if resolved_indicator == SET_INDICATOR else "SEF"
            extracted[f"{prefix} period simulation score"] = str(
                evaluation_period.get("points") or 0
            )
        if evaluation_period.get("issues"):
            extracted["Evaluation period issues"] = "; ".join(evaluation_period["issues"][:4])
    stamp_simulation_metadata(
        extracted,
        eligible=simulation_eligible,
        points=provisional_display,
        auto_approved=auto_approve,
        awaiting_reviewer=not auto_approve,
        ocr_reliable=extraction.reliable,
        fields_ok=fields_ok,
        scoring_ok=scoring_ok,
        identity_ok=identity_ok,
        indicator_id=resolved_indicator,
        evidence_attestation_required=bool(evidence_reason),
        package_needs_reviewer=bool(evidence_assessment.get("needsReviewer")),
    )
    if reviewer_correction and correction_entries:
        from reviewer_metadata import merge_correction_log

        log_json, extras = merge_correction_log(
            prior_extracted_info,
            reviewer_id=str(reviewer_correction.get("reviewer_id") or ""),
            reason=str(reviewer_correction.get("reason") or ""),
            new_entries=correction_entries,
        )
        extracted["Reviewer correction log"] = log_json
        extracted.update(extras)
    elif prior_extracted_info:
        if prior_extracted_info.get("Reviewer correction log"):
            extracted["Reviewer correction log"] = prior_extracted_info["Reviewer correction log"]
        for key, value in prior_extracted_info.items():
            if str(key).startswith("OCR original —"):
                extracted[key] = value

    missing_title = not title
    if (
        is_rating_aggregation
        and aggregated_indicator_points is not None
        and aggregated_indicator_points > 0
        and auto_approve
    ):
        extracted["Scoring status"] = "Automatically Scored"
        extracted["Simulation score source"] = "System-calculated"
        extracted["Processing branch"] = "Complete and valid"

    return {
        "kra": kra,
        "criterion_id": criterion_id,
        "indicator_id": resolved_indicator,
        "author_count": authors,
        "base_points": base,
        "contribution_percent": percent,
        # Document-level points stay 0 for SET/SEF semesters; indicator totals use period aggregation.
        "points": credited_points,
        "exact_points": 0.0 if missing_title or not identity_ok else provisional_display,
        "extracted_info": extracted,
        "extracted_text": text,
        "file_hash": file_hash(file_path),
        "flagged_for_review": not auto_approve,
        "status": status,
        "validation_result": validation,
        "auto_approved": auto_approve,
        "simulation_eligible": simulation_eligible,
        "simulation_points": int(round(provisional_display)) if simulation_eligible else 0,
        "evaluation_period": evaluation_period,
        "_fields_ok": fields_ok,
        "_identity_ok": identity_ok,
        "_evidence_assessment": evidence_assessment,
    }


def _archive_simulation_if_version_changed(sim, previous_version: int, config_version: int):
    if previous_version and previous_version != config_version:
        from datetime import datetime, timezone

        history = list(sim.history or [])
        history.append(
            {
                "kraConfigVersion": previous_version,
                "currentPoints": sim.current_points,
                "requiredPoints": sim.required_points,
                "eligibilityLabel": sim.eligibility_label,
                "areasToImprove": sim.areas_to_improve or [],
                "formula": sim.scoring_formula,
                "archivedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
        sim.history = history[-20:]


def summarize_documents(
    documents,
    config: dict,
    current_rank: str | None,
    *,
    evaluation_records=None,
) -> dict:
    """Rank simulation totals using effective simulation scores (system or reviewer-adjusted)."""
    from simulation_scoring import build_simulation_indicator_entries

    targets = config.get("targets") or dict(KRA_TARGETS)
    weight_band, applied_weights = weights_for_rank(config, current_rank)
    counts = {kra: 0 for kra in targets}
    entries, includes_pending = build_simulation_indicator_entries(
        documents, config, evaluation_records=evaluation_records
    )
    best_by_indicator: dict[str, tuple] = {}
    for entry in entries:
        indicator_id = entry.get("indicator_id")
        earned = float(entry.get("points") or 0)
        if not indicator_id or earned <= 0:
            continue
        for doc in documents:
            if getattr(doc, "indicator_id", None) == indicator_id:
                kra = getattr(doc, "kra", None)
                if kra in targets:
                    best_by_indicator[indicator_id] = (earned, kra, doc)
                break
    credited = credited_kra_totals(entries, config)
    totals = {kra: float(credited.get(kra, 0.0)) for kra in targets}
    for earned, kra, _doc in best_by_indicator.values():
        if earned > 0:
            counts[kra] = counts.get(kra, 0) + 1
    for kra, target in targets.items():
        totals[kra] = min(totals.get(kra, 0.0), float(target))
    weighted = weighted_final_score(totals, applied_weights)
    eligibility = "Potentially Eligible" if weighted >= 41 else "Pending"
    areas = [
        {
            "kra": kra,
            "recommendedPoints": int(round(max(targets[kra] - totals.get(kra, 0), 0))),
            "guidance": (
                f"Add documentary evidence for {kra}. "
                f"Table 2.2 weight for {weight_band}: {int(applied_weights.get(kra, 0))}%."
            ),
        }
        for kra in targets
        if totals.get(kra, 0) < targets[kra]
    ]
    return {
        "targets": targets,
        "totals": totals,
        "counts": counts,
        "weighted": weighted,
        "weightBand": weight_band,
        "appliedWeights": applied_weights,
        "includesPending": includes_pending,
        "eligibility": eligibility,
        "areas": areas,
        "snapshot": {
            "targets": targets,
            "criteria": config.get("criteria") or {},
            "indicators": config.get("indicators") or {},
            "rankWeights": config.get("rankWeights") or {},
            "weightBand": weight_band,
            "appliedWeights": applied_weights,
            "kraPoints": {kra: round(totals.get(kra, 0.0), 2) for kra in targets},
            "verifiedKraPoints": {kra: round(totals.get(kra, 0.0), 2) for kra in targets},
            "weightedScore": weighted,
            "includesPending": includes_pending,
            "pendingExcluded": False,
            "simulationIncludesAutoScored": True,
            "publishedAt": config.get("publishedAt") or "",
            "status": config.get("status") or "published",
        },
    }


def reconcile_automatic_approvals(user, documents, config) -> None:
    """Re-score pending uploads with full SET/SEF context so valid documents auto-approve."""
    from kra1a_evaluation import RATING_AGGREGATION_INDICATORS

    active = [doc for doc in documents if getattr(doc, "deleted_at", None) is None]
    eval_context = [
        doc
        for doc in active
        if getattr(doc, "indicator_id", None) in RATING_AGGREGATION_INDICATORS
    ]
    for doc in active:
        status = (getattr(doc, "status", None) or "").strip()
        if status in PROTECTED_DOC_STATUSES:
            continue
        if status not in RECONCILABLE_STATUSES:
            continue
        if getattr(doc, "reviewer_score", None) is not None:
            continue
        if getattr(doc, "decided_at", None) or getattr(doc, "review_snapshot", None):
            continue
        path = getattr(doc, "file_path", None)
        stored_text = None
        if not path or not Path(path).exists():
            stored_text = getattr(doc, "extracted_text", None) or ""
        processed = process_upload(
            title=doc.title,
            author=doc.author,
            file_path=str(path) if stored_text is None and path else None,
            stored_ocr_text=stored_text,
            declared_kra=doc.kra,
            criterion_id=doc.criterion_id,
            indicator_id=doc.indicator_id,
            config=config,
            existing_docs=[item for item in active if item is not doc],
            uploader_name=user.profile.full_name if user.profile else None,
            prior_extracted_info=doc.extracted_info,
            evaluation_context_documents=eval_context,
            current_public_id=getattr(doc, "public_id", "") or "",
        )
        doc.status = processed["status"]
        doc.points = processed["points"]
        doc.flagged_for_review = processed["flagged_for_review"]
        doc.validation_result = processed["validation_result"]
        doc.extracted_info = processed["extracted_info"]
        doc.simulation_points = processed.get("simulation_points") or 0
        if processed.get("indicator_id"):
            doc.indicator_id = processed["indicator_id"]
        if processed.get("extracted_text") and not getattr(doc, "extracted_text", None):
            doc.extracted_text = processed["extracted_text"]


def refresh_user_scores(user, Document, KraScore, RankSimulation, db, EvaluationRecord=None):
    from simulation_scoring import stamp_evaluation_period_metadata

    config = load_active_kra_config(db)
    current_rank = user.profile.current_rank if user.profile else "Instructor I"
    active_docs = [d for d in user.documents if getattr(d, "deleted_at", None) is None]
    evaluation_records = []
    if EvaluationRecord is not None:
        from kra1a_workflow import backfill_evaluation_records

        backfill_evaluation_records(user, active_docs, EvaluationRecord=EvaluationRecord, db=db)
        evaluation_records = (
            EvaluationRecord.query.filter_by(user_id=user.id)
            .filter(EvaluationRecord.deleted_at.is_(None))
            .all()
        )
    reconcile_automatic_approvals(user, active_docs, config)
    stamp_evaluation_period_metadata(active_docs, evaluation_records=evaluation_records)
    summary = summarize_documents(
        user.documents, config, current_rank, evaluation_records=evaluation_records
    )
    targets = summary["targets"]
    totals = summary["totals"]
    counts = summary["counts"]
    weighted = summary["weighted"]

    for kra, target in targets.items():
        current = min(totals.get(kra, 0.0), float(target))
        totals[kra] = current
        row = next((item for item in user.kra_scores if item.kra == kra), None)
        if row is None:
            row = KraScore(user_id=user.id, kra=kra, target_points=target)
            db.session.add(row)
        row.current_points = int(round(current))
        row.target_points = int(target)
        row.document_count = counts.get(kra, 0)
        remaining = max(target - current, 0)
        if remaining == 0:
            row.status_label = "On track"
        elif current == 0:
            row.status_label = "Needs attention"
        else:
            row.status_label = "In progress"

    # Table 2.2 weighted final score (0–100), using the faculty member's rank band.
    required = 100
    sim = user.simulation
    if sim is None:
        sim = RankSimulation(
            user_id=user.id,
            current_rank=current_rank,
            target_rank="Instructor II",
            required_points=required,
        )
        db.session.add(sim)
    else:
        _archive_simulation_if_version_changed(
            sim,
            int(sim.kra_config_version or 0),
            int(config.get("version") or 0),
        )

    sim.current_points = int(round(weighted))
    sim.required_points = required
    sim.kra_config_version = int(config.get("version") or 0)
    sim.scoring_formula = WEIGHTED_FORMULA
    sim.config_snapshot = summary["snapshot"]
    if user.profile:
        sim.current_rank = user.profile.current_rank
    sim.eligibility_label = summary["eligibility"]
    sim.areas_to_improve = summary["areas"]
    return sim
