"""Reviewer metadata correction helpers."""

import json

from reviewer_metadata import (
    apply_field_overrides,
    fields_from_extracted_info,
    merge_correction_log,
)


def test_fields_from_extracted_info_uses_academic_year_as_date():
    fields = fields_from_extracted_info(
        {"Extracted names": "Maria Santos", "Academic year": "AY 2023-2024", "Extracted rating": "95"}
    )
    assert fields["date"] == "AY 2023-2024"
    assert fields["rating"] == 95.0
    assert fields["named_parties"] == ["Maria Santos"]


def test_apply_field_overrides_records_audit_entries():
    base = {"named_parties": [], "authors": [], "date": "", "rating": None, "title": ""}
    updated, entries = apply_field_overrides(
        base,
        {
            "facultyName": "Jason Baroro",
            "academicYear": "AY 2023-2024",
            "evaluationRating": "95",
        },
    )
    assert updated["named_parties"] == ["Jason Baroro"]
    assert updated["date"] == "AY 2023-2024"
    assert updated["rating"] == 95.0
    assert len(entries) == 3


def test_merge_correction_log_preserves_ocr_baseline():
    prior = {"Extracted names": "", "Provisional score": "0"}
    log_json, extras = merge_correction_log(
        prior,
        reviewer_id="42",
        reason="Name visible on page 1",
        new_entries=[{"field": "facultyName", "label": "Faculty", "original": "", "corrected": "Jason Baroro"}],
    )
    log = json.loads(log_json)
    assert log[0]["reviewerId"] == "42"
    assert extras["OCR baseline captured"] == "yes"
    assert "OCR original — Extracted names" in extras
