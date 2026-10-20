"""Reviewer approval snapshots and single-score validation."""

import importlib.util
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
WEB_ASSETS = BACKEND.parent / "assets" / "js"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _load_web():
    spec = importlib.util.spec_from_file_location("facultylink_web_app_award", BACKEND / "app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["facultylink_web_app_award"] = module
    spec.loader.exec_module(module)
    return module


def _kra_settings():
    return {
        "indicators": {
            "kra1-a-student": {"maxPoints": 36, "contribution": "not-applicable"},
            "kra2-a-journal-sole": {"maxPoints": 50, "contribution": "sole"},
            "kra2-a-journal-declared": {"maxPoints": 50, "contribution": "declared"},
        }
    }


def test_set_rating_review_uses_full_assigned_score():
    web = _load_web()
    incoming = {
        "indicatorId": "kra1-a-student",
        "review": {
            "indicatorId": "kra1-a-student",
            "kraId": "instruction",
            "criterionId": "kra1-a",
            "officialMax": 36,
            "officialPoints": 36,
            "officialLabel": "(rating ÷ 100) × 36",
            "contributionPercent": 100,
            "assignedScore": 34.2,
        },
    }
    snapshot, error = web.awarded_review(incoming, _kra_settings())
    assert error is None
    assert snapshot["assignedScore"] == 34.2
    assert snapshot["finalScore"] == 34.2
    assert snapshot["contributionPercent"] == 100


def test_declared_contribution_applies_percent():
    web = _load_web()
    incoming = {
        "review": {
            "indicatorId": "kra2-a-journal-declared",
            "kraId": "research",
            "criterionId": "kra2-a",
            "officialMax": 50,
            "contributionPercent": 40,
            "assignedScore": 50,
        },
    }
    snapshot, error = web.awarded_review(incoming, _kra_settings())
    assert error is None
    assert snapshot["finalScore"] == 20.0


def test_non_declared_indicator_rejects_authorship_percent():
    web = _load_web()
    incoming = {
        "review": {
            "indicatorId": "kra1-a-student",
            "kraId": "instruction",
            "criterionId": "kra1-a",
            "officialMax": 36,
            "contributionPercent": 50,
            "assignedScore": 34.2,
        },
    }
    snapshot, error = web.awarded_review(incoming, _kra_settings())
    assert snapshot is None
    assert "Contribution percentage" in error


def test_assigned_score_cannot_exceed_official_max():
    web = _load_web()
    incoming = {
        "review": {
            "indicatorId": "kra1-a-student",
            "officialMax": 36,
            "contributionPercent": 100,
            "assignedScore": 40,
        },
    }
    snapshot, error = web.awarded_review(incoming, _kra_settings())
    assert snapshot is None
    assert error


def test_reviewer_ui_exposes_one_editable_score_field():
    documents_js = (WEB_ASSETS / "documents.js").read_text(encoding="utf-8")
    assert "assigned-score" not in documents_js
    assert 'id="decision-score"' in documents_js
    assert documents_js.count('id="decision-score"') == 1
