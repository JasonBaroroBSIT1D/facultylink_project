"""Per-item evidence package validation."""

from types import SimpleNamespace

from evidence_validation import STATE_SYSTEM_VERIFIED, assess_package_requirements


def _doc(text: str, requirement_index: int | None = None):
    return SimpleNamespace(
        extracted_text=text,
        extracted_info={"Evidence requirement index": requirement_index} if requirement_index is not None else {},
        requirement_index=requirement_index,
        deleted_at=None,
        public_id="doc-1",
    )


def test_single_evidence_system_verified_with_matching_ocr():
    ocr = "student evaluation template overall rating semester faculty instruction"
    assessment = assess_package_requirements(
        "kra1-a-student",
        [_doc(ocr)],
        fields_ok=True,
        identity_ok=True,
    )
    assert assessment["requirements"]
    assert assessment["requirements"][0]["state"] in {STATE_SYSTEM_VERIFIED, "uploaded_unverified"}


def test_multi_evidence_incomplete_without_files():
    assessment = assess_package_requirements(
        "kra1-b-textbook-sole",
        [_doc("textbook only")],
        fields_ok=True,
        identity_ok=True,
    )
    assert assessment["completeValid"] is False
    assert assessment["missingLabels"] or assessment["uncertainLabels"]
