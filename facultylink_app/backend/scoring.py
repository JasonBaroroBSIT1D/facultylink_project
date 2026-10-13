import hashlib
import re
from pathlib import Path

from ocr import extract_text

KRA_TARGETS = {
    "instruction": 30,
    "research": 30,
    "extension": 20,
    "professionalDevelopment": 20,
}

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


def contribution_score(base_points: int, authors: int) -> int:
    if authors <= 0:
        authors = 1
    return round(base_points * (1 / authors))


def process_upload(*, title: str, author: str | None, file_path: str | None, declared_kra: str | None):
    text = extract_text(file_path)
    combined = " ".join(part for part in (title, author, text) if part)
    kra, ambiguous = classify_kra(combined, declared_kra)
    authors = author_count(author)
    base = KRA_BASE_POINTS.get(kra, 5)
    points = contribution_score(base, authors)
    extracted = {
        "Document type": "Uploaded documentary evidence",
        "Assigned KRA": kra,
        "Author count": str(authors),
        "Base points": str(base),
        "Contribution score": str(points),
    }
    if text.strip():
        extracted["OCR excerpt"] = text.strip()[:280]
    else:
        extracted["OCR"] = "Tesseract was not available or the file had no readable text. Keyword rules used the title and author."

    missing_fields = not title or not author
    flagged = missing_fields or ambiguous or not text.strip()
    validation = (
        "Flagged for reviewer validation."
        if flagged
        else "Processed with rule-based scoring. Awaiting reviewer confirmation."
    )
    return {
        "kra": kra,
        "author_count": authors,
        "base_points": base,
        "points": 0 if flagged and missing_fields else points,
        "extracted_info": extracted,
        "extracted_text": text,
        "file_hash": file_hash(file_path),
        "flagged_for_review": True,
        "status": "pendingReview",
        "validation_result": validation,
    }


def refresh_user_scores(user, Document, KraScore, RankSimulation, db):
    docs = [doc for doc in user.documents if doc.status == "validated"]
    totals = {kra: 0 for kra in KRA_TARGETS}
    counts = {kra: 0 for kra in KRA_TARGETS}
    for doc in docs:
        totals[doc.kra] = totals.get(doc.kra, 0) + (doc.points or 0)
        counts[doc.kra] = counts.get(doc.kra, 0) + 1

    for kra, target in KRA_TARGETS.items():
        current = totals.get(kra, 0)
        row = next((item for item in user.kra_scores if item.kra == kra), None)
        if row is None:
            row = KraScore(user_id=user.id, kra=kra, target_points=target)
            db.session.add(row)
        row.current_points = current
        row.document_count = counts.get(kra, 0)
        remaining = max(target - current, 0)
        if remaining == 0:
            row.status_label = "On track"
        elif current == 0:
            row.status_label = "Needs attention"
        else:
            row.status_label = "In progress"

    total = sum(totals.values())
    required = sum(KRA_TARGETS.values())
    sim = user.simulation
    if sim is None:
        sim = RankSimulation(
            user_id=user.id,
            current_rank=user.profile.current_rank if user.profile else "Instructor I",
            target_rank="Instructor II",
            required_points=required,
        )
        db.session.add(sim)
    sim.current_points = total
    sim.required_points = required
    if user.profile:
        sim.current_rank = user.profile.current_rank
    sim.eligibility_label = "Potentially Eligible" if total >= 60 else "Pending"
    sim.areas_to_improve = [
        {
            "kra": kra,
            "recommendedPoints": max(KRA_TARGETS[kra] - totals.get(kra, 0), 0),
            "guidance": f"Add documentary evidence for {kra} to close the remaining gap.",
        }
        for kra in KRA_TARGETS
        if totals.get(kra, 0) < KRA_TARGETS[kra]
    ]
    return sim
