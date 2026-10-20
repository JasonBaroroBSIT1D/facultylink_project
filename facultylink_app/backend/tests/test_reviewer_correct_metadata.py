"""Reviewer metadata correction eligibility and scoring config loading."""

import os

import pytest

from document_lifecycle import metadata_correction_block_reason
from kra_config import scoring_config_from_kra_row
from reviewer_metadata import ALLOWED_OVERRIDE_KEYS


def test_metadata_correction_block_reason_pending():
    assert metadata_correction_block_reason({"status": "pendingReview", "decided_at": None}) is None


def test_metadata_correction_block_reason_validated():
    reason = metadata_correction_block_reason({"status": "validated", "decided_at": None})
    assert reason and "final decision" in reason.lower()


def test_metadata_correction_block_reason_decided_at():
    reason = metadata_correction_block_reason({"status": "pendingReview", "decided_at": "2024-01-01"})
    assert reason


def test_scoring_config_from_kra_row_without_updated_at():
    row = {
        "payload": '{"kras": {}}',
        "version": 2,
        "status": "published",
        "published_at": "2024-01-01",
        "formula": "Custom formula",
    }
    config = scoring_config_from_kra_row(row)
    assert config["version"] == 2
    assert config["formula"] == "Custom formula"


def test_allowed_override_keys_match_reviewer_form():
    expected = {
        "facultyName",
        "extractedTitle",
        "academicYear",
        "academicTerm",
        "evaluationRating",
    }
    assert expected.issubset(ALLOWED_OVERRIDE_KEYS)


INTEGRATION = os.environ.get("FACULTYLINK_INTEGRATION") == "1"


@pytest.mark.skipif(not INTEGRATION, reason="Set FACULTYLINK_INTEGRATION=1 to run web API tests.")
def test_web_correct_metadata_http_responses():
    import importlib.util
    import sys
    import uuid
    from pathlib import Path

    web_backend = Path(__file__).resolve().parents[2].parent / "facultylink_web" / "backend"
    if str(web_backend) not in sys.path:
        sys.path.insert(0, str(web_backend))
    spec = importlib.util.spec_from_file_location("facultylink_web_correct_http", web_backend / "app.py")
    web = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(web)

    conn = web.connect()
    reviewer = conn.execute(
        """
        SELECT u.id, d.public_id
        FROM users u
        JOIN faculty_profiles fp ON fp.reviewer_user_id = u.id
        JOIN documents d ON d.user_id = fp.user_id
        WHERE u.role = 'reviewer'
          AND d.status = 'pendingReview'
          AND d.decided_at IS NULL
          AND d.deleted_at IS NULL
        ORDER BY d.id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    if not reviewer:
        pytest.skip("No pending document with assigned reviewer.")

    client = web.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = reviewer["id"]
        sess["role"] = "reviewer"
    doc_id = reviewer["public_id"]

    bad_reason = client.post(
        f"/api/documents/{doc_id}/correct-metadata",
        json={"reason": "short", "facultyName": "X"},
    )
    assert bad_reason.status_code == 400
    assert "8 characters" in bad_reason.get_json()["error"]

    no_fields = client.post(
        f"/api/documents/{doc_id}/correct-metadata",
        json={"reason": "Verified on original document"},
    )
    assert no_fields.status_code == 400

    unique = f"HTTP-Test-{uuid.uuid4().hex[:8]}"
    ok = client.post(
        f"/api/documents/{doc_id}/correct-metadata",
        json={"reason": "Verified on original PDF page 1", "facultyName": unique},
    )
    assert ok.status_code == 200
