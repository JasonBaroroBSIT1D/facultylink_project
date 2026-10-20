"""SET / FEDAF-style evaluation summaries (faculty name, AY, rating)."""

from document_validation import (
    extract_document_period,
    extract_fields,
    extract_named_parties,
    extract_rating,
    verify_identity,
)
from scoring import process_upload

JASON_SET_TEXT = """
Student Evaluation of Teaching
Faculty: Jason Baroro
Faculty Subject: Jason Baroro
Academic Year: 2023-2024
Academic Term: 1st Semester
Evaluation Type: Student Evaluation of Teaching
Overall Rating: 95.00 / 100
""".strip()


def test_faculty_colon_label_extracts_name():
    label, names, from_document = extract_named_parties(
        ocr_text=JASON_SET_TEXT,
        upload_author=None,
        indicator_id="kra1-a-student",
    )
    assert from_document is True
    assert label == "Faculty Name"
    assert names == ["Jason Baroro"]


def test_academic_year_and_overall_rating_extracted():
    assert extract_document_period(ocr_text=JASON_SET_TEXT) == "2023-2024"
    assert extract_rating(JASON_SET_TEXT) == 95.0
    fields = extract_fields(
        title="SET Summary",
        author=None,
        ocr_text=JASON_SET_TEXT,
        indicator_id="kra1-a-student",
    )
    assert fields["date"] == "2023-2024"
    assert fields["academic_term"] == "1st Semester"
    assert fields["evaluation_type"] == "Student Evaluation of Teaching"
    assert fields["rating"] == 95.0


def test_identity_matched_for_uploader():
    fields = extract_fields(
        title="SET",
        author=None,
        ocr_text=JASON_SET_TEXT,
        indicator_id="kra1-a-student",
    )
    ok, _label, message = verify_identity(
        "kra1-a-student",
        uploader_name="Jason Baroro",
        named_parties=fields["named_parties"],
    )
    assert ok is True
    assert message == "Identity matched."


def test_set_without_rating_does_not_use_instruction_fallback_points(tmp_path):
    path = tmp_path / "set-no-rating.txt"
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
    assert float(result["extracted_info"]["Provisional score"]) == 0.0


def test_set_full_pipeline_with_text_file(tmp_path):
    path = tmp_path / "set.txt"
    path.write_text(JASON_SET_TEXT, encoding="utf-8")
    result = process_upload(
        title="SET Summary",
        author=None,
        file_path=str(path),
        declared_kra="instruction",
        criterion_id="kra1-a",
        indicator_id="kra1-a-student",
        uploader_name="Jason Baroro",
    )
    info = result["extracted_info"]
    assert "Jason Baroro" in info["Extracted names"]
    assert info["Academic year"] == "2023-2024"
    assert info["Extracted rating"] == "95.0"
    assert info["Identity verification"] == "Identity matched."
    assert float(info["Provisional score"]) == 0.0
    assert result["status"] == "system_approved"


def test_set_digital_pdf_template(tmp_path):
    import pymupdf

    path = tmp_path / "jason-set.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    y = 72
    for line in JASON_SET_TEXT.splitlines():
        page.insert_text((72, y), line, fontsize=12)
        y += 22
    pdf.save(path)
    pdf.close()
    result = process_upload(
        title="SET Summary",
        author=None,
        file_path=str(path),
        declared_kra="instruction",
        criterion_id="kra1-a",
        indicator_id="kra1-a-student",
        uploader_name="Jason Baroro",
    )
    info = result["extracted_info"]
    assert "Jason Baroro" in info["Extracted names"]
    assert info["Academic year"] == "2023-2024"
    assert info["Identity verification"] == "Identity matched."
    assert float(info["Provisional score"]) == 0.0
    assert result["status"] == "system_approved"


def test_missing_faculty_name_stays_unverified():
    text = "Student Evaluation of Teaching\nOverall Rating: 90.00 / 100\nAcademic Year: 2023-2024\n"
    label, names, from_document = extract_named_parties(
        ocr_text=text,
        upload_author=None,
        indicator_id="kra1-a-student",
    )
    assert from_document is False
    assert names == []
    ok, _label, message = verify_identity(
        "kra1-a-student",
        uploader_name="Jason Baroro",
        named_parties=names,
    )
    assert ok is False
    assert "no faculty name was extracted" in message.lower()
