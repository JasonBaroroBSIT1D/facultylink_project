"""JC 2026 Criterion A regression — SET/SEF aggregation and consolidated extraction."""

from types import SimpleNamespace

from kra1a_evaluation import SEF_INDICATOR, SET_INDICATOR, aggregate_criterion_a, aggregate_rating_indicator
from kra1a_record_extraction import extract_semester_records


def _set_doc(public_id: str, ay: str, sem: str, rating: float):
    return SimpleNamespace(
        public_id=public_id,
        indicator_id=SET_INDICATOR,
        deleted_at=None,
        reviewer_score=None,
        status="system_approved",
        extracted_info={
            "Academic year": ay,
            "Academic term": f"Semester {sem}",
            "Extracted rating": str(rating),
        },
    )


def _sef_doc(public_id: str, ay: str, sem: str, rating: float):
    return SimpleNamespace(
        public_id=public_id,
        indicator_id=SEF_INDICATOR,
        deleted_at=None,
        reviewer_score=None,
        status="system_approved",
        extracted_info={
            "Academic year": ay,
            "Academic term": f"Semester {sem}",
            "Extracted rating": str(rating),
        },
    )


def test_guideline_set_example():
    docs = [
        _set_doc("d1", "2023-2024", "1", 95),
        _set_doc("d2", "2023-2024", "2", 89),
        _set_doc("d3", "2024-2025", "1", 88),
        _set_doc("d4", "2024-2025", "2", 92),
        _set_doc("d5", "2025-2026", "1", 94),
        _set_doc("d6", "2025-2026", "2", 85),
    ]
    result = aggregate_rating_indicator(docs, SET_INDICATOR)
    assert result["averageRating"] == 90.5
    assert result["points"] == 32.58


def test_guideline_sef_example():
    ratings = [90, 92, 94, 90, 91, 95]
    docs = []
    pairs = [
        ("2023-2024", "1"),
        ("2023-2024", "2"),
        ("2024-2025", "1"),
        ("2024-2025", "2"),
        ("2025-2026", "1"),
        ("2025-2026", "2"),
    ]
    for idx, (ay, sem) in enumerate(pairs):
        docs.append(_sef_doc(f"s{idx}", ay, sem, ratings[idx]))
    result = aggregate_rating_indicator(docs, SEF_INDICATOR)
    assert result["averageRating"] == 92.0
    assert result["points"] == 22.08


def test_guideline_combined_criterion_a():
    set_docs = [
        _set_doc("d1", "2023-2024", "1", 95),
        _set_doc("d2", "2023-2024", "2", 89),
        _set_doc("d3", "2024-2025", "1", 88),
        _set_doc("d4", "2024-2025", "2", 92),
        _set_doc("d5", "2025-2026", "1", 94),
        _set_doc("d6", "2025-2026", "2", 85),
    ]
    sef_ratings = [90, 92, 94, 90, 91, 95]
    sef_docs = []
    pairs = [
        ("2023-2024", "1"),
        ("2023-2024", "2"),
        ("2024-2025", "1"),
        ("2024-2025", "2"),
        ("2025-2026", "1"),
        ("2025-2026", "2"),
    ]
    for idx, (ay, sem) in enumerate(pairs):
        sef_docs.append(_sef_doc(f"s{idx}", ay, sem, sef_ratings[idx]))
    total = aggregate_criterion_a(set_docs + sef_docs)
    assert total["criterionPoints"] == 54.66


def test_consolidated_pdf_extracts_four_records():
    text = """
    Academic Year 2025-2026
    1st Semester SET: 98.80
    1st Semester SEF: 100.00
    2nd Semester SET: 96.10
    2nd Semester SEF: 98.67
    Faculty Name: Maria Santos
    """
    records = extract_semester_records(ocr_text=text, title="AY 2025-2026 Summary")
    assert len(records) == 4
    keys = {(r.indicator_id, r.academic_year, r.semester) for r in records}
    assert (SET_INDICATOR, "2025-2026", "1") in keys
    assert (SEF_INDICATOR, "2025-2026", "1") in keys
    assert (SET_INDICATOR, "2025-2026", "2") in keys
    assert (SEF_INDICATOR, "2025-2026", "2") in keys
