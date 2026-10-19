from pathlib import Path

import pytest

from document_validation import (
    extract_fields,
    extract_named_parties,
    extract_rating,
    find_duplicate_accomplishment,
    validate_indicator_fields,
    verify_identity,
)
from scoring import classify_kra, process_upload


class _Doc:
    def __init__(self, public_id, indicator_id, title, status, file_hash=None):
        self.public_id = public_id
        self.indicator_id = indicator_id
        self.title = title
        self.status = status
        self.file_hash = file_hash


def test_classify_kra_no_match_is_not_ambiguous():
    kra, ambiguous = classify_kra("Student Evaluation SET rating 92", fallback="instruction")
    assert kra == "instruction"
    assert ambiguous is False


def test_extract_rating_from_set_summary():
    rating = extract_rating("Overall SET rating: 92 percent for AY 2024-2025")
    assert rating == 92.0


def test_extract_faculty_name_from_set_document():
    label, names, _from_document = extract_named_parties(
        ocr_text="Student Evaluation of Teachers\nFaculty Name: Maria Santos\nOverall SET rating: 90",
        upload_author=None,
        indicator_id="kra1-a-student",
    )
    assert label == "Faculty Name"
    assert any("Maria Santos" in name for name in names)


def test_extract_participant_name_from_certificate():
    label, names, _from_document = extract_named_parties(
        ocr_text="Certificate of Participation\nParticipant Name: Jose Reyes\nDate: March 10, 2024",
        upload_author=None,
        indicator_id="kra4-a-training",
    )
    assert label == "Participant Name"
    assert names[0] == "Jose Reyes"


def test_identity_mismatch_flags_review():
    ok, _, message = verify_identity(
        "kra1-a-student",
        uploader_name="Maria Santos",
        named_parties=["Pedro Cruz"],
    )
    assert ok is False
    assert "does not match" in message


def test_validate_set_requires_rating_and_period():
    fields = extract_fields(
        title="SET Summary",
        author="Maria Santos",
        ocr_text="Student Evaluation of Teachers SET",
    )
    ok, reasons = validate_indicator_fields("kra1-a-student", fields, ocr_text="Student Evaluation")
    assert ok is False
    assert any("rating" in reason.lower() for reason in reasons)


def test_duplicate_accomplishment_detects_same_indicator_title():
    existing = [
        _Doc("doc-a", "kra2-a-journal-sole", "Journal Article on Inquiry", "system_approved"),
    ]
    match = find_duplicate_accomplishment(
        existing,
        indicator_id="kra2-a-journal-sole",
        title="Journal Article on Inquiry",
    )
    assert match == "doc-a"


def test_process_upload_auto_approves_journal_with_ocr(tmp_path: Path):
    path = tmp_path / "journal.txt"
    path.write_text(
        "Peer-reviewed journal article ISSN 2244-1180 with abstract. "
        "Author Maria Santos. Published March 15, 2024.",
        encoding="utf-8",
    )
    result = process_upload(
        title="Journal Article on Inquiry Classrooms",
        author="Maria Santos",
        file_path=str(path),
        declared_kra="research",
        criterion_id="kra2-a",
        uploader_name="Maria Santos",
    )
    assert result["indicator_id"] == "kra2-a-journal-sole"
    assert result["status"] == "system_approved"
    assert result["points"] > 0


def test_process_upload_pending_when_classification_weak(tmp_path: Path):
    path = tmp_path / "vague.txt"
    path.write_text("Miscellaneous scanned page without indicator terms.", encoding="utf-8")
    result = process_upload(
        title="Untitled",
        author="Maria Santos",
        file_path=str(path),
        declared_kra="research",
        criterion_id="kra2-a",
    )
    assert result["status"] == "pendingReview"
    assert result["extracted_info"].get("Review reasons")


def test_process_upload_auto_approves_set_with_rating(tmp_path: Path):
    path = tmp_path / "set.txt"
    path.write_text(
        "Student Evaluation of Teachers (SET).\nFaculty Name: Maria Santos\n"
        "Overall SET rating: 88. SY 2024-2025.",
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
    assert result["indicator_id"] == "kra1-a-student"
    assert result["status"] == "system_approved"
    assert result["points"] == 32
