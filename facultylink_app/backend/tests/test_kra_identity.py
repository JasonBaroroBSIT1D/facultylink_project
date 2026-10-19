"""Representative identity extraction tests for all four KRAs."""

from document_validation import extract_fields, extract_named_parties, validate_indicator_fields, verify_identity
from indicator_identity import resolve_identity_profile


def test_kra1_set_faculty_name_profile():
    profile = resolve_identity_profile("kra1-a-student")
    assert profile.display_label == "Faculty Name"
    label, names, _from_document = extract_named_parties(
        ocr_text="Faculty Name: Ana Reyes\nOverall SET rating: 91",
        upload_author=None,
        indicator_id="kra1-a-student",
    )
    assert label == "Faculty Name"
    assert "Ana Reyes" in names[0]


def test_kra1_adviser_requires_match():
    ok, _, msg = verify_identity(
        "kra1-c-adviser-mt",
        uploader_name="Pedro Cruz",
        named_parties=["Maria Santos"],
    )
    assert ok is False
    assert "does not match" in msg


def test_kra2_journal_author_extraction():
    fields = extract_fields(
        title="Study on wetlands",
        author=None,
        ocr_text="Authors: Pedro Cruz; Maria Santos\nISSN 1234-5678\n2024",
        indicator_id="kra2-a-journal-co",
    )
    ocr = "Authors: Pedro Cruz; Maria Santos\nISSN 1234-5678\n2024"
    ok, reasons = validate_indicator_fields("kra2-a-journal-co", fields, ocr_text=ocr)
    assert len(fields["named_parties"]) >= 1
    assert ok is True


def test_kra2_inventor_label():
    profile = resolve_identity_profile("kra2-b-patent-g-sole")
    assert profile.display_label == "Inventor(s)"
    label, names, _from_document = extract_named_parties(
        ocr_text="Inventor: Jose Reyes\nPatent Grant No. 123",
        upload_author=None,
        indicator_id="kra2-b-patent-g-sole",
    )
    assert label == "Inventor(s)"


def test_kra3_extension_participant():
    label, names, _from_document = extract_named_parties(
        ocr_text="Participant: Maria Santos\nCommunity outreach 2024",
        upload_author="Maria Santos",
        indicator_id="kra3-b-ext-participant",
    )
    assert names
    ok, _, _ = verify_identity(
        "kra3-b-ext-participant",
        uploader_name="Maria Santos",
        named_parties=names,
    )
    assert ok is True


def test_kra3_admin_designation_employee_name():
    profile = resolve_identity_profile("kra3-d-dean")
    assert profile.mode == "admin_designation"
    label, names, _from_document = extract_named_parties(
        ocr_text="Employee Name: Maria Santos\nDesignation: Dean",
        upload_author=None,
        indicator_id="kra3-d-dean",
    )
    assert "Maria Santos" in names[0]


def test_kra4_awardee_extraction():
    label, names, _from_document = extract_named_parties(
        ocr_text="Certificate of Recognition\nAwardee: Maria Santos\nMarch 2024",
        upload_author=None,
        indicator_id="kra4-c-inst",
    )
    assert label == "Awardee"
    fields = extract_fields(
        title="Institutional award",
        author=None,
        ocr_text="Awardee: Maria Santos\nMarch 2024",
        indicator_id="kra4-c-inst",
    )
    ok, reasons = validate_indicator_fields("kra4-c-inst", fields, ocr_text="Awardee: Maria Santos")
    assert ok is True
    assert not reasons


def test_kra4_participant_certificate():
    label, names, _from_document = extract_named_parties(
        ocr_text="Certificate of Participation\nParticipant Name: Jose Reyes",
        upload_author=None,
        indicator_id="kra4-b-part-local",
    )
    assert label == "Participant Name"
    assert names[0] == "Jose Reyes"
