"""A logged-in faculty member must not receive credit for another faculty member's document."""

from pathlib import Path

from document_validation import extract_named_parties
from scoring import process_upload

UPLOADER = "Maria Santos"


def _upload(tmp_path: Path, text: str, **kwargs):
    path = tmp_path / "evidence.txt"
    path.write_text(text, encoding="utf-8")
    return process_upload(
        title=kwargs.get("title", "SET Rating Summary"),
        author=kwargs.get("author", UPLOADER),
        file_path=str(path),
        declared_kra=kwargs.get("kra", "instruction"),
        criterion_id=kwargs.get("criterion", "kra1-a"),
        uploader_name=kwargs.get("uploader", UPLOADER),
        contribution_percent=kwargs.get("share"),
    )


def test_account_name_is_compared_not_the_upload_form(tmp_path: Path):
    result = _upload(
        tmp_path,
        "Student Evaluation of Teachers (SET)\nFaculty Name: Pedro Cruz\n"
        "Overall SET rating: 90\nAcademic Year 2024-2025\n",
        author="Pedro Cruz",
    )
    info = result["extracted_info"]
    assert result["status"] == "pendingReview"
    assert result["points"] == 0
    assert info["Extracted names"] == "Pedro Cruz"
    assert "does not match" in info["Identity verification"]
    assert result["validation_result"].startswith("Extracted faculty name does not match")
    assert float(info["Provisional score"]) == 0.0
    assert float(info["Extracted rating"]) == 90.0


def test_name_on_the_following_line_is_not_part_of_the_subject(tmp_path: Path):
    result = _upload(
        tmp_path,
        "Student Evaluation of Teachers (SET)\nFaculty Name: Pedro Cruz\n"
        "Maria Santos\nOverall SET rating: 90\nAcademic Year 2024-2025\n",
    )
    assert result["status"] == "pendingReview"
    assert result["points"] == 0
    assert result["extracted_info"]["Extracted names"] == "Pedro Cruz"


def test_preparer_signatory_and_certifier_are_not_the_owner(tmp_path: Path):
    preparer = _upload(
        tmp_path,
        "Student Evaluation of Teachers (SET)\nOverall SET rating: 90\n"
        "Academic Year 2024-2025\nPrepared by: Maria Santos\n",
    )
    assert preparer["status"] == "pendingReview"
    assert preparer["points"] == 0
    assert preparer["extracted_info"]["Extracted names"] == ""

    signatory = _upload(
        tmp_path,
        "Student Evaluation of Teachers (SET)\nOverall SET rating: 90\n"
        "Academic Year 2024-2025\nSignatory: Maria Santos\nCertified by: Maria Santos\n"
        "Supervisor: Maria Santos\n",
    )
    assert signatory["status"] == "pendingReview"
    assert signatory["points"] == 0
    assert "was not extracted" in signatory["extracted_info"]["Identity verification"] or signatory["extracted_info"]["Extracted names"] == ""


def test_subject_wins_when_a_preparer_is_also_named(tmp_path: Path):
    result = _upload(
        tmp_path,
        "Student Evaluation of Teachers (SET)\nFaculty Name: Pedro Cruz\n"
        "Overall SET rating: 90\nAcademic Year 2024-2025\n"
        "Prepared by: Maria Santos\nCertified by: Maria Santos\n",
    )
    assert result["extracted_info"]["Extracted names"] == "Pedro Cruz"
    assert result["status"] == "pendingReview"
    assert result["points"] == 0


def test_matching_owner_is_still_approved(tmp_path: Path):
    result = _upload(
        tmp_path,
        "Student Evaluation of Teachers (SET)\nFaculty Name: Maria Santos\n"
        "Overall SET rating: 90\nAcademic Year 2024-2025\nPrepared by: Alex Reyes\n",
    )
    assert result["status"] == "system_approved"
    assert result["points"] == 0
    assert result["extracted_info"]["Extracted names"] == "Maria Santos"


def test_linkage_signatory_remains_a_valid_identity_label():
    label, names, from_document = extract_named_parties(
        ocr_text="Memorandum of Agreement\nSignatory: Maria Santos\nMarch 10, 2024",
        upload_author=None,
        indicator_id="kra3-a-linkage",
    )
    assert from_document is True
    assert label == "Signatory"
    assert names[0] == "Maria Santos"


def test_coauthor_is_recognized_and_sole_claim_is_not_approved(tmp_path: Path):
    result = _upload(
        tmp_path,
        "Peer-reviewed journal article ISSN 2244-1180 with abstract.\n"
        "Authors: Pedro Cruz; Maria Santos\nPublished March 15, 2024.\n",
        title="Journal Article on Inquiry Classrooms",
        kra="research",
        criterion="kra2-a",
        share=50,
    )
    assert "Maria Santos" in result["extracted_info"]["Extracted names"]
    assert "Pedro Cruz" in result["extracted_info"]["Extracted names"]
    assert result["status"] == "pendingReview"
    assert result["extracted_info"]["Identity verification"] == "Identity matched."
