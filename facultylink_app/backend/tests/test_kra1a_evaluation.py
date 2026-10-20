"""KRA I Criterion A SET/SEF six-semester aggregation."""

from types import SimpleNamespace

from kra1a_evaluation import SET_INDICATOR, aggregate_rating_indicator, collect_evaluation_slots


def _set_doc(public_id: str, ay: str, sem: str, rating: float):
    return SimpleNamespace(
        public_id=public_id,
        indicator_id=SET_INDICATOR,
        deleted_at=None,
        reviewer_score=None,
        status="pendingReview",
        extracted_info={
            "Academic year": ay,
            "Academic term": f"Semester {sem}",
            "Extracted rating": str(rating),
        },
    )


def test_set_six_semester_average_and_points():
    docs = [
        _set_doc("d1", "2023-2024", "1", 95),
        _set_doc("d2", "2023-2024", "2", 89),
        _set_doc("d3", "2024-2025", "1", 88),
        _set_doc("d4", "2024-2025", "2", 92),
        _set_doc("d5", "2025-2026", "1", 94),
        _set_doc("d6", "2025-2026", "2", 85),
    ]
    result = aggregate_rating_indicator(docs, SET_INDICATOR)
    assert result["finalized"] is True
    assert result["averageRating"] == 90.5
    assert result["points"] == 32.58
    assert result["maxPoints"] == 36.0


def test_set_semester_inferred_from_document_title():
    doc = SimpleNamespace(
        public_id="d-sem2",
        indicator_id=SET_INDICATOR,
        deleted_at=None,
        reviewer_score=None,
        status="pendingReview",
        title="06 SET AY2025 2026 Sem2",
        file_name="06_SET_AY2025-2026_Sem2.pdf",
        extracted_info={
            "Academic year": "2025-2026",
            "Extracted rating": "85",
        },
    )
    slots, issues = collect_evaluation_slots([doc], SET_INDICATOR)
    assert len(slots) == 1
    assert slots[0].semester == "2"
    assert not any("missing academic year" in i for i in issues)


def test_set_incomplete_period_not_finalized():
    docs = [
        _set_doc("d1", "2023-2024", "1", 95),
        _set_doc("d2", "2023-2024", "2", 89),
        _set_doc("d3", "2024-2025", "1", 88),
        _set_doc("d4", "2024-2025", "2", 92),
        _set_doc("d5", "2025-2026", "1", 94),
    ]
    result = aggregate_rating_indicator(docs, SET_INDICATOR)
    assert result["finalized"] is False
    assert result["coverageComplete"] is False
    assert result["filledCount"] == 5
    assert result["points"] == 0.0
    assert any("Incomplete evaluation-period coverage" in issue for issue in result["issues"])
