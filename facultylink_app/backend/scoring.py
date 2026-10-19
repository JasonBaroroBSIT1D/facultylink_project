import hashlib
import re
from pathlib import Path

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
    if scored["matched"] and scored["base_points"] is not None:
        base = scored["base_points"]
        percent = scored["contribution_percent"] or 100.0
        points = scored["points"]
    else:
        base = KRA_BASE_POINTS.get(kra, 5)
        percent = round(100.0 / max(authors, 1), 2)
        points = final_score(base, percent)

    review_reasons: list[str] = list(classification.reasons)
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

    evidence = (rule_for(resolved_indicator) or {}).get("evidence") or []
    evidence_reason = None
    if resolved_indicator and len(evidence) != 1:
        evidence_reason = (
            "Annex A requires documentary evidence that cannot be confirmed from this file alone, "
            "so a reviewer must verify it before points are credited."
        )
        review_reasons.append(evidence_reason)

    auto_approve = (
        bool(criterion_id)
        and classification.reliable
        and bool(resolved_indicator)
        and fields_ok
        and scoring_ok
        and auth_ok
        and identity_ok
        and evidence_reason is None
        and duplicate_of is None
        and contradiction is None
        and text.strip()
        and extraction.reliable
        and scored["matched"]
        and scored["base_points"] is not None
        and not scored.get("flagged")
    )

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
        "Extracted rating": str(effective_rating) if effective_rating is not None else "",
        "Base points": str(base),
        "Contribution percent": str(percent),
        "Scoring formula": SCORING_FORMULA,
        "Provisional score": str(points),
        "Contribution score": str(points),
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
    extracted["Verification tier"] = "System approved" if auto_approve else "Pending review"

    missing_title = not title
    return {
        "kra": kra,
        "criterion_id": criterion_id,
        "indicator_id": resolved_indicator,
        "author_count": authors,
        "base_points": base,
        "contribution_percent": percent,
        # points is the credited value. Only system-approved uploads store it.
        # The calculated figure always remains in Provisional score.
        "points": int(round(points)) if auto_approve else 0,
        "exact_points": 0.0 if missing_title or not identity_ok else points,
        "extracted_info": extracted,
        "extracted_text": text,
        "file_hash": file_hash(file_path),
        "flagged_for_review": not auto_approve,
        "status": status,
        "validation_result": validation,
        "auto_approved": auto_approve,
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


def summarize_documents(documents, config: dict, current_rank: str | None) -> dict:
    """Credited KRA totals for verified documents. Pending and rejected rows add nothing."""
    targets = config.get("targets") or dict(KRA_TARGETS)
    weight_band, applied_weights = weights_for_rank(config, current_rank)
    counts = {kra: 0 for kra in targets}
    best_by_indicator: dict[str, tuple] = {}
    includes_pending = False
    for doc in documents:
        status = getattr(doc, "status", None)
        if status in PROVISIONAL_STATUSES:
            includes_pending = True
            continue
        if status not in VERIFIED_STATUSES:
            continue
        kra = getattr(doc, "kra", None)
        if kra not in targets:
            continue
        earned = document_earned_points(doc, config)
        if earned <= 0:
            continue
        key = getattr(doc, "indicator_id", None) or getattr(doc, "public_id", None)
        current = best_by_indicator.get(key)
        if current is None or earned > current[0]:
            best_by_indicator[key] = (earned, kra, doc)

    entries = [
        {"indicator_id": getattr(doc, "indicator_id", None), "points": earned}
        for earned, _kra, doc in best_by_indicator.values()
    ]
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
            "pendingExcluded": True,
            "publishedAt": config.get("publishedAt") or "",
            "status": config.get("status") or "published",
        },
    }


def refresh_user_scores(user, Document, KraScore, RankSimulation, db):
    config = load_active_kra_config(db)
    current_rank = user.profile.current_rank if user.profile else "Instructor I"
    summary = summarize_documents(user.documents, config, current_rank)
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
