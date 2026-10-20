"""HTTP tests for correct-metadata (require FACULTYLINK_INTEGRATION=1 and PostgreSQL)."""

import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

INTEGRATION = os.environ.get("FACULTYLINK_INTEGRATION") == "1"


def _load_web():
    spec = importlib.util.spec_from_file_location("facultylink_web_app_correct_meta", BACKEND / "app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["facultylink_web_app_correct_meta"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not INTEGRATION, reason="Set FACULTYLINK_INTEGRATION=1 to run against PostgreSQL.")
def test_correct_metadata_400_short_reason():
    web = _load_web()
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
        pytest.skip("No pending document with assigned reviewer in database.")
    client = web.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = reviewer["id"]
        sess["role"] = "reviewer"
    response = client.post(
        f"/api/documents/{reviewer['public_id']}/correct-metadata",
        json={"reason": "too short", "facultyName": "Test Faculty"},
    )
    assert response.status_code == 400
    assert "8 characters" in response.get_json()["error"]


@pytest.mark.skipif(not INTEGRATION, reason="Set FACULTYLINK_INTEGRATION=1 to run against PostgreSQL.")
def test_correct_metadata_403_faculty():
    web = _load_web()
    conn = web.connect()
    faculty = conn.execute(
        """
        SELECT u.id, d.public_id
        FROM users u
        JOIN documents d ON d.user_id = u.id
        WHERE u.role = 'faculty' AND d.deleted_at IS NULL
        ORDER BY d.id DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    if not faculty:
        pytest.skip("No faculty-owned document in database.")
    client = web.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = faculty["id"]
        sess["role"] = "faculty"
    response = client.post(
        f"/api/documents/{faculty['public_id']}/correct-metadata",
        json={"reason": "Should not be allowed", "facultyName": "Someone"},
    )
    assert response.status_code == 403


@pytest.mark.skipif(not INTEGRATION, reason="Set FACULTYLINK_INTEGRATION=1 to run against PostgreSQL.")
def test_correct_metadata_409_after_final_decision():
    web = _load_web()
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
    if not reviewer:
        conn.close()
        pytest.skip("No pending document with assigned reviewer in database.")
    row = conn.execute(
        "SELECT status, decided_at FROM documents WHERE public_id = %s",
        (reviewer["public_id"],),
    ).fetchone()
    client = web.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = reviewer["id"]
        sess["role"] = "reviewer"
    try:
        conn.execute(
            "UPDATE documents SET status = %s, decided_at = %s WHERE public_id = %s",
            ("validated", "2024-06-01 12:00:00", reviewer["public_id"]),
        )
        conn.commit()
        response = client.post(
            f"/api/documents/{reviewer['public_id']}/correct-metadata",
            json={"reason": "Attempt after approval", "facultyName": "New Name"},
        )
        assert response.status_code == 409
        assert "final decision" in response.get_json()["error"].lower()
    finally:
        conn.execute(
            "UPDATE documents SET status = %s, decided_at = %s WHERE public_id = %s",
            (row["status"], row["decided_at"], reviewer["public_id"]),
        )
        conn.commit()
        conn.close()


@pytest.mark.skipif(not INTEGRATION, reason="Set FACULTYLINK_INTEGRATION=1 to run against PostgreSQL.")
def test_correct_metadata_500_when_pipeline_fails(monkeypatch):
    web = _load_web()
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
        pytest.skip("No pending document with assigned reviewer in database.")
    import scoring

    monkeypatch.setattr(scoring, "process_upload", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("pipeline unavailable")))
    client = web.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = reviewer["id"]
        sess["role"] = "reviewer"
    response = client.post(
        f"/api/documents/{reviewer['public_id']}/correct-metadata",
        json={"reason": "Trigger pipeline failure path", "facultyName": "Fail Case"},
    )
    assert response.status_code == 500
    assert "Could not apply metadata correction" in response.get_json()["error"]


@pytest.mark.skipif(not INTEGRATION, reason="Set FACULTYLINK_INTEGRATION=1 to run against PostgreSQL.")
def test_correct_metadata_success_persists():
    web = _load_web()
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
        pytest.skip("No pending document with assigned reviewer in database.")
    unique = f"Reviewer-Correct-{uuid.uuid4().hex[:8]}"
    client = web.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = reviewer["id"]
        sess["role"] = "reviewer"
    response = client.post(
        f"/api/documents/{reviewer['public_id']}/correct-metadata",
        json={"reason": "Verified on original PDF page 1", "facultyName": unique},
    )
    assert response.status_code == 200
    conn = web.connect()
    stored = conn.execute(
        "SELECT extracted_info FROM documents WHERE public_id = %s",
        (reviewer["public_id"],),
    ).fetchone()
    conn.close()
    info = stored["extracted_info"] if isinstance(stored["extracted_info"], dict) else {}
    assert info.get("Extracted names") == unique or unique in str(info)
