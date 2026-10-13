import hashlib
import re
from pathlib import Path

from kra_config import (
    DEFAULT_KRA_MAX,
    SCORING_FORMULA,
    WEIGHTED_FORMULA,
    document_earned_points,
    final_score,
    load_active_kra_config,
    weighted_final_score,
    weights_for_rank,
)
from ocr import extract_text

# Fallback targets when kra_settings is unavailable (Annex I maxima).
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
        return fallback or "instruction", True
    matches.sort()
    return matches[0][1], len(matches) > 1


def contribution_score(base_points: float, authors: int) -> float:
    """Provisional equal-share estimate using the shared web formula."""
    if authors <= 0:
        authors = 1
    percent = round(100.0 / authors, 2)
    return final_score(base_points, percent)


def process_upload(*, title: str, author: str | None, file_path: str | None, declared_kra: str | None):
    text = extract_text(file_path)
    combined = " ".join(part for part in (title, author, text) if part)
    kra, ambiguous = classify_kra(combined, declared_kra)
    authors = author_count(author)
    base = KRA_BASE_POINTS.get(kra, 5)
    percent = round(100.0 / max(authors, 1), 2)
    points = final_score(base, percent)
    extracted = {
        "Document type": "Uploaded documentary evidence",
        "Assigned KRA": kra,
        "Author count": str(authors),
        "Base points": str(base),
        "Contribution percent": str(percent),
        "Scoring formula": SCORING_FORMULA,
        "Contribution score": str(points),
    }
    if text.strip():
        extracted["OCR excerpt"] = text.strip()[:280]
    else:
        extracted["OCR"] = "Tesseract was not available or the file had no readable text. Keyword rules used the title and author."

    missing_title = not title
    flagged = missing_title or ambiguous or not text.strip()
    validation = (
        "Flagged for reviewer validation."
        if flagged
        else "Processed with rule-based scoring. Awaiting reviewer confirmation."
    )
    return {
        "kra": kra,
        "author_count": authors,
        "base_points": base,
        "points": 0 if missing_title else int(round(points)),
        "extracted_info": extracted,
        "extracted_text": text,
        "file_hash": file_hash(file_path),
        "flagged_for_review": True,
        "status": "pendingReview",
        "validation_result": validation,
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


def refresh_user_scores(user, Document, KraScore, RankSimulation, db):
    config = load_active_kra_config(db)
    targets = config.get("targets") or dict(KRA_TARGETS)
    current_rank = user.profile.current_rank if user.profile else "Instructor I"
    weight_band, applied_weights = weights_for_rank(config, current_rank)

    docs = [doc for doc in user.documents if doc.status == "validated"]
    totals = {kra: 0.0 for kra in targets}
    counts = {kra: 0 for kra in targets}
    for doc in docs:
        kra = doc.kra if doc.kra in targets else None
        if kra is None:
            continue
        earned = document_earned_points(doc, config)
        totals[kra] = totals.get(kra, 0.0) + earned
        counts[kra] = counts.get(kra, 0) + 1

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
    weighted = weighted_final_score(totals, applied_weights)
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
    sim.config_snapshot = {
        "targets": targets,
        "criteria": config.get("criteria") or {},
        "indicators": config.get("indicators") or {},
        "rankWeights": config.get("rankWeights") or {},
        "weightBand": weight_band,
        "appliedWeights": applied_weights,
        "kraPoints": {kra: round(totals.get(kra, 0.0), 2) for kra in targets},
        "weightedScore": weighted,
        "publishedAt": config.get("publishedAt") or "",
        "status": config.get("status") or "published",
    }
    if user.profile:
        sim.current_rank = user.profile.current_rank
    # Table 3.1 starts awarding sub-ranks at 41; use that as a preview threshold only.
    sim.eligibility_label = "Potentially Eligible" if weighted >= 41 else "Pending"
    sim.areas_to_improve = [
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
    return sim
