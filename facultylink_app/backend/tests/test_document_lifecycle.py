"""Document delete, replace permissions, and scoring exclusion."""

from datetime import datetime, timezone

import pytest

from app import app, db
from document_lifecycle import faculty_may_delete, faculty_may_replace, is_active, metadata_correction_block_reason
from models import Document, User
from scoring import summarize_documents


def _pending_doc(user_id, **kwargs):
    doc = Document(
        public_id="doc-test01",
        user_id=user_id,
        title="Test Upload",
        category="supportingEvidence",
        kra="instruction",
        status="pendingReview",
        points=0,
        file_name="test.pdf",
        criterion_id="kra1-a",
    )
    for key, value in kwargs.items():
        setattr(doc, key, value)
    return doc


def test_deleted_documents_are_excluded_from_totals():
    class _Doc:
        pass

    active = _Doc()
    active.status = "validated"
    active.kra = "instruction"
    active.points = 20
    active.reviewer_score = 20
    active.indicator_id = "kra1-b-module-sole"
    active.public_id = "active"
    active.deleted_at = None

    deleted = _Doc()
    deleted.status = "validated"
    deleted.kra = "instruction"
    deleted.points = 30
    deleted.reviewer_score = 30
    deleted.indicator_id = "kra1-b-textbook-sole"
    deleted.public_id = "deleted"
    deleted.deleted_at = datetime.now(timezone.utc)

    config = {"targets": {"instruction": 60}}
    only_deleted = summarize_documents([deleted], config, "Instructor I")
    only_active = summarize_documents([active], config, "Instructor I")
    assert only_deleted["totals"]["instruction"] == 0
    assert only_active["totals"]["instruction"] > 0


def test_soft_deleted_documents_are_not_active():
    doc = _pending_doc(1)
    assert is_active(doc)
    doc.deleted_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    assert not is_active(doc)


def test_cannot_delete_validated_document():
    doc = _pending_doc(1, status="validated", reviewer_score=10.0, decided_at="2026-01-01")
    allowed, message = faculty_may_delete(doc)
    assert not allowed
    assert "withdrawal" in message.lower() or "decision" in message.lower()


def test_may_delete_pending_without_decision():
    doc = _pending_doc(1)
    assert faculty_may_delete(doc) == (True, "")


def test_may_replace_needs_revision():
    doc = _pending_doc(1, status="needsRevision")
    assert faculty_may_replace(doc) == (True, "")


def test_faculty_delete_api(client):
    from test_api import faculty_headers

    headers = faculty_headers(client)
    with app.app_context():
        user = User.query.filter_by(email="maria.santos@university.edu.ph").first()
        doc = _pending_doc(user.id, public_id="doc-deltest")
        db.session.add(doc)
        db.session.commit()
    response = client.delete("/api/documents/doc-deltest", headers=headers)
    assert response.status_code == 200
    listed = client.get("/api/documents", headers=headers).get_json()
    assert all(item["id"] != "doc-deltest" for item in listed)
    with app.app_context():
        row = Document.query.filter_by(public_id="doc-deltest").first()
        assert row.deleted_at is not None


def test_faculty_cannot_delete_validated_document(client):
    from test_api import faculty_headers

    headers = faculty_headers(client)
    with app.app_context():
        user = User.query.filter_by(email="maria.santos@university.edu.ph").first()
        doc = _pending_doc(
            user.id,
            public_id="doc-prot1",
            status="validated",
            reviewer_score=8.0,
            decided_at="2026-01-01",
            points=8,
        )
        db.session.add(doc)
        db.session.commit()
    response = client.delete("/api/documents/doc-prot1", headers=headers)
    assert response.status_code == 409
