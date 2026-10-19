from document_classifier import classify_within_criterion
from document_validation import extract_fields, validate_indicator_fields


def test_classify_journal_within_research_criterion():
    result = classify_within_criterion(
        "kra2-a",
        title="Journal publication study",
        author="Maria Santos",
        ocr_text="Peer-reviewed journal article ISSN 2244-1180 abstract March 15, 2024",
        authors_count=1,
    )
    assert result.indicator_id == "kra2-a-journal-sole"
    assert result.reliable is True


def test_journal_fields_require_publication_metadata():
    fields = extract_fields(
        title="Journal Article",
        author="Maria Santos",
        ocr_text="Peer-reviewed journal ISSN 1234-5678. Author: Maria Santos. Published 2024-03-15.",
        indicator_id="kra2-a-journal-sole",
    )
    ok, reasons = validate_indicator_fields(
        "kra2-a-journal-sole",
        fields,
        ocr_text="Peer-reviewed journal ISSN 1234-5678. Author: Maria Santos. Published 2024-03-15.",
    )
    assert ok is True
    assert not reasons
