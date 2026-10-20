"""Automatic rank-simulation scoring for complete + valid documents."""

from pathlib import Path

from kra1a_evaluation import SET_INDICATOR
from scoring import process_upload, reconcile_automatic_approvals, summarize_documents
from simulation_scoring import document_effective_simulation_points


class _Doc:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _set_doc(ay: str, sem: str, rating: float, **extra):
    return _Doc(
        status="pendingReview",
        kra="instruction",
        points=0,
        indicator_id=SET_INDICATOR,
        deleted_at=None,
        extracted_info={
            "Academic year": ay,
            "Academic term": f"Semester {sem}",
            "Extracted rating": str(rating),
            "Simulation eligible": "yes",
            **extra,
        },
    )


def test_single_set_upload_not_finalized_until_six_semesters(tmp_path: Path):
    path = tmp_path / "set.txt"
    path.write_text(
        "Student Evaluation Rating Summary FEDAF template SET.\nFaculty Name: Maria Santos\n"
        "Overall SET rating: 88. Academic Year 2024-2025. Semester 1.",
        encoding="utf-8",
    )
    result = process_upload(
        title="SET Rating Summary",
        author="Maria Santos",
        file_path=str(path),
        declared_kra="instruction",
        criterion_id="kra1-a",
        uploader_name="Maria Santos",
    )
    assert result["status"] == "system_approved"
    assert result["simulation_eligible"] is False
    assert result["extracted_info"].get("Evaluation period coverage") == "Incomplete"
    doc = _Doc(
        status="pendingReview",
        kra="instruction",
        points=0,
        indicator_id=SET_INDICATOR,
        extracted_info=result["extracted_info"],
        simulation_points=result["simulation_points"],
    )
    assert document_effective_simulation_points(doc) is None


def test_set_six_semesters_auto_approve_and_aggregate():
    class _User:
        profile = type("P", (), {"full_name": "Maria Santos"})()

    ratings = [
        ("2023-2024", "1", 95),
        ("2023-2024", "2", 89),
        ("2024-2025", "1", 88),
        ("2024-2025", "2", 92),
        ("2025-2026", "1", 94),
        ("2025-2026", "2", 85),
    ]
    docs = []
    for idx, (ay, sem, rating) in enumerate(ratings):
        docs.append(
            _Doc(
                status="pendingReview",
                kra="instruction",
                points=0,
                indicator_id=SET_INDICATOR,
                criterion_id="kra1-a",
                public_id=f"doc-set-{idx}",
                title=f"SET AY {ay} Sem {sem}",
                author="Maria Santos",
                file_path=None,
                extracted_text=f"Student Evaluation of Teachers SET\nFaculty Name: Maria Santos\nOverall SET rating: {rating}\nAcademic Year {ay} Semester {sem}",
                extracted_info={
                    "Academic year": ay,
                    "Academic term": f"Semester {sem}",
                    "Extracted rating": str(rating),
                },
            )
        )
    config = {
        "targets": {
            "instruction": 100,
            "research": 100,
            "extension": 100,
            "professionalDevelopment": 100,
        },
        "criteria": {},
        "indicators": {},
        "rankWeights": {},
    }
    reconcile_automatic_approvals(_User(), docs, config)
    assert all(doc.status == "system_approved" for doc in docs)
    assert all(doc.points == 0 for doc in docs)
    summary = summarize_documents(docs, config, "Instructor I")
    assert summary["totals"]["instruction"] == 32.58


def test_set_six_semesters_count_once_in_simulation():
    docs = [
        _set_doc("2023-2024", "1", 95),
        _set_doc("2023-2024", "2", 89),
        _set_doc("2024-2025", "1", 88),
        _set_doc("2024-2025", "2", 92),
        _set_doc("2025-2026", "1", 94),
        _set_doc("2025-2026", "2", 85),
    ]
    summary = summarize_documents(
        docs,
        {
            "targets": {
                "instruction": 100,
                "research": 100,
                "extension": 100,
                "professionalDevelopment": 100,
            },
            "criteria": {},
            "indicators": {},
            "rankWeights": {},
        },
        "Instructor I",
    )
    assert summary["totals"]["instruction"] == 32.58


def test_incomplete_set_has_no_simulation_score(tmp_path: Path):
    path = tmp_path / "set-incomplete.txt"
    path.write_text(
        "Faculty: Jason Baroro\nAcademic Year: 2023-2024\nStudent Evaluation of Teaching\n",
        encoding="utf-8",
    )
    result = process_upload(
        title="SET Summary",
        author=None,
        file_path=str(path),
        declared_kra="instruction",
        criterion_id="kra1-a",
        indicator_id="kra1-a-student",
        uploader_name="Jason Baroro",
    )
    assert result["simulation_eligible"] is False
    doc = _Doc(
        status="pendingReview",
        kra="instruction",
        points=0,
        indicator_id="kra1-a-student",
        extracted_info=result["extracted_info"],
    )
    assert document_effective_simulation_points(doc) is None


def test_reviewer_adjusted_overrides_system_score():
    info = {
        "Simulation eligible": "yes",
        "System-calculated score": "15",
        "Provisional score": "15",
    }
    doc = _Doc(
        status="validated",
        kra="research",
        points=15,
        reviewer_score=12.0,
        indicator_id="kra2-a-journal-sole",
        extracted_info=info,
    )
    assert document_effective_simulation_points(doc) == 12.0


def test_rejected_document_excluded_from_simulation():
    from simulation_scoring import mark_simulation_removed

    info = mark_simulation_removed(
        {"Simulation eligible": "yes", "System-calculated score": "32"},
        reason="Rejected by reviewer",
    )
    doc = _Doc(status="invalid", kra="instruction", points=0, indicator_id="kra1-a-student", extracted_info=info)
    assert document_effective_simulation_points(doc) is None
