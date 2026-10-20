"""Reviewer approval blockers and metadata correction authorization."""

import importlib.util
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _load_web():
    spec = importlib.util.spec_from_file_location("facultylink_web_app_approval", BACKEND / "app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["facultylink_web_app_approval"] = module
    spec.loader.exec_module(module)
    return module


def test_approval_blocked_when_set_rating_missing():
    web = _load_web()
    row = {
        "indicator_id": "kra1-a-student",
        "extracted_text": "Student evaluation summary",
        "extracted_info": {
            "Extracted names": "Jason Baroro",
            "Academic year": "AY 2023-2024",
            "Extracted rating": "",
        },
    }
    blockers = web.document_approval_blockers(row, "kra1-a-student", uploader_name="Jason Baroro")
    assert any("rating" in b["message"].lower() for b in blockers)


def test_approval_allowed_after_verified_set_fields():
    web = _load_web()
    row = {
        "indicator_id": "kra1-a-student",
        "extracted_text": (
            "Student Evaluation Rating Summary FEDAF template SET overall rating semester faculty"
        ),
        "extracted_info": {
            "Extracted names": "Jason Baroro",
            "Academic year": "AY 2023-2024",
            "Academic term": "Semester 1",
            "Extracted rating": "95",
            "Reviewer verified extraction": "yes",
            "Identity verification": "Identity matched.",
        },
    }
    blockers = web.document_approval_blockers(row, "kra1-a-student", uploader_name="Jason Baroro")
    assert blockers == []


def test_multi_evidence_requires_attestation():
    web = _load_web()
    row = {
        "indicator_id": "kra1-b-textbook-sole",
        "extracted_text": "Textbook ISBN 978-0-123456-78-9 instructional material 2024",
        "extracted_info": {
            "Extracted title": "Engineering Textbook",
            "Extracted names": "Maria Santos",
            "Extracted date": "2024",
        },
    }
    blockers = web.document_approval_blockers(row, "kra1-b-textbook-sole", uploader_name="Maria Santos")
    assert any(b["kind"] == "missing_evidence" for b in blockers)
