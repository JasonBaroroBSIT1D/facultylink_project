"""Reprocess stored OCR text after reviewer field overrides."""

from scoring import process_upload


SET_TEXT = """
STUDENT EVALUATION OF TEACHERS AND INSTRUCTION (SET)
Faculty: Jason Baroro
Academic Year: 2023-2024
Semester: First Semester
Overall Rating: 95.00 / 100
"""


def test_stored_text_correction_fills_rating_and_recomputes_provisional():
    prior = {"Extracted names": "", "Extracted rating": ""}
    result = process_upload(
        title="SET Summary",
        author="Jason Baroro",
        file_path=None,
        declared_kra="instruction",
        criterion_id="kra1-a",
        indicator_id="kra1-a-student",
        stored_ocr_text=SET_TEXT,
        field_overrides={"facultyName": "Jason Baroro", "evaluationRating": "95", "academicYear": "AY 2023-2024"},
        prior_extracted_info=prior,
        reviewer_correction={"reviewer_id": "9", "reason": "Verified on original PDF"},
        force_manual_review=True,
        uploader_name="Jason Baroro",
    )
    info = result["extracted_info"]
    assert info["Extracted names"] == "Jason Baroro"
    assert float(info["Extracted rating"]) == 95.0
    assert float(info["Provisional score"]) == 0.0
    assert "Reviewer correction log" in info
    assert result["auto_approved"] is False
