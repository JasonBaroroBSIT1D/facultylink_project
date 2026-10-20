"""Credited totals, identity, and auto-approval against Annex A of JC No. 01, s. 2026."""

from pathlib import Path

from document_validation import _names_similar, extract_named_parties, verify_identity
from indicator_identity import resolve_identity_profile
from indicator_rules import load_indicator_rules, load_scoring_structure
from kra_config import credited_kra_totals, weighted_final_score, weights_for_rank
from scoring import process_upload, summarize_documents


def test_annex_structure_has_bonus_criteria_and_evidence():
    structure = load_scoring_structure()
    assert structure["criteria"]["kra1-a"]["maxPoints"] == 60
    assert structure["criteria"]["kra1-b"]["maxPoints"] == 30
    assert structure["criteria"]["kra1-c"]["maxPoints"] == 10
    assert structure["criteria"]["kra3-d"]["bonus"] is True
    assert structure["criteria"]["kra4-d"]["bonus"] is True
    assert structure["kras"]["kra3"]["bonusMax"] == 20
    assert structure["kras"]["kra4"]["bonusMax"] == 20
    rules = load_indicator_rules()
    assert len(rules["kra1-a-student"]["evidence"]) == 1
    assert len(rules["kra2-a-journal-sole"]["evidence"]) == 1
    assert len(rules["kra1-b-textbook-sole"]["evidence"]) > 1
    assert len(rules["kra2-c-conducting"]["evidence"]) > 1
    assert len(rules["kra2-c-dance-perf"]["evidence"]) > 1


def test_criterion_cap_stops_instructional_materials_at_30():
    totals = credited_kra_totals(
        [
            {"indicator_id": "kra1-b-textbook-sole", "points": 30},
            {"indicator_id": "kra1-b-module-sole", "points": 16},
        ]
    )
    assert totals["instruction"] == 30


def test_kra_cap_and_bonus_cannot_exceed_100():
    totals = credited_kra_totals(
        [
            {"indicator_id": "kra3-a-linkage", "points": 5},
            {"indicator_id": "kra3-b-ext-head", "points": 30},
            {"indicator_id": "kra3-c-satisfaction", "points": 20},
            {"indicator_id": "kra3-d-president", "points": 20},
        ]
    )
    assert totals["extension"] == 75

    full = credited_kra_totals(
        [
            {"indicator_id": "kra3-a-income-lead-over", "points": 18},
            {"indicator_id": "kra3-a-income-lead-12m", "points": 12},
            {"indicator_id": "kra3-b-ext-head", "points": 30},
            {"indicator_id": "kra3-b-qa-intl", "points": 10},
            {"indicator_id": "kra3-b-consult-intl", "points": 10},
            {"indicator_id": "kra3-c-satisfaction", "points": 20},
            {"indicator_id": "kra3-d-president", "points": 20},
        ]
    )
    assert full["extension"] == 100


def test_research_criteria_share_the_kra_maximum():
    totals = credited_kra_totals(
        [
            {"indicator_id": "kra2-a-book-sole", "points": 100},
            {"indicator_id": "kra2-b-patent-g-sole", "points": 80},
        ]
    )
    assert totals["research"] == 100


def test_group_cap_limits_additional_degrees():
    totals = credited_kra_totals(
        [
            {"indicator_id": "kra4-b-doctorate", "points": 40},
            {"indicator_id": "kra4-b-masters", "points": 20},
        ]
    )
    assert totals["professionalDevelopment"] == 40


def test_published_criterion_maximum_is_honored():
    totals = credited_kra_totals(
        [{"indicator_id": "kra1-b-textbook-sole", "points": 30}],
        {"criteria": {"kra1-b": {"maxPoints": 10}}, "targets": {}, "indicators": {}},
    )
    assert totals["instruction"] == 10


def test_rank_weights_use_capped_kra_totals():
    totals = {"instruction": 100, "research": 0, "extension": 100, "professionalDevelopment": 0}
    _band, weights = weights_for_rank({}, "Instructor I")
    # 100 × 60% + 100 × 20% = 80. Pending points are not part of this input.
    assert weighted_final_score(totals, weights) == 80


def test_partial_name_does_not_match_full_name():
    assert _names_similar("Maria", "Maria Santos") is False
    assert _names_similar("Maria Santos", "Maria Santos") is True
    assert _names_similar("Maria C. Santos", "Maria Santos") is True
    ok, _, message = verify_identity(
        "kra1-a-student",
        uploader_name="Maria Santos",
        named_parties=["Maria"],
    )
    assert ok is False
    assert "does not match" in message


def test_conducting_and_dance_use_performer_identity():
    conducting = resolve_identity_profile("kra2-c-conducting")
    dance = resolve_identity_profile("kra2-c-dance-perf")
    assert conducting.mode == "performer"
    assert dance.mode == "performer"
    assert conducting.require_named_party is True
    label, names, from_document = extract_named_parties(
        ocr_text="Conductor\nMaria Santos\nMarch 12, 2024",
        upload_author=None,
        indicator_id="kra2-c-conducting",
    )
    assert from_document is True
    assert label == "Conductor"
    assert names[0] == "Maria Santos"
    label, names, _from_document = extract_named_parties(
        ocr_text="Performer: Maria Santos\nJune 2, 2024",
        upload_author=None,
        indicator_id="kra2-c-dance-perf",
    )
    assert names[0] == "Maria Santos"


def test_multi_evidence_indicator_stays_pending(tmp_path: Path):
    path = tmp_path / "textbook.txt"
    path.write_text(
        "Sole author of a textbook.\nAuthor: Maria Santos\nPublished March 15, 2024.\nISBN 978-123-45678-9.",
        encoding="utf-8",
    )
    result = process_upload(
        title="College Algebra",
        author="Maria Santos",
        file_path=str(path),
        declared_kra="instruction",
        criterion_id="kra1-b",
        indicator_id="kra1-b-textbook-sole",
        uploader_name="Maria Santos",
    )
    assert result["status"] == "pendingReview"
    assert result["points"] == 0
    assert float(result["extracted_info"]["Provisional score"]) > 0
    reasons = result["extracted_info"]["Review reasons"]
    assert "Supporting evidence" in reasons or "missing" in reasons.lower()


def test_single_evidence_set_can_still_be_approved(tmp_path: Path):
    path = tmp_path / "set.txt"
    path.write_text(
        "Student Evaluation of Teachers (SET).\nFaculty Name: Maria Santos\n"
        "Overall SET rating: 88. SY 2024-2025.",
        encoding="utf-8",
    )
    result = process_upload(
        title="SET Rating Summary",
        author="Maria Santos",
        file_path=str(path),
        declared_kra="instruction",
        criterion_id="kra1-a",
        uploader_name="Maria Santos",
    )
    assert result["status"] == "system_approved"
    assert result["points"] == 0
    assert result["extracted_info"]["Validation status"] == "Valid"
    assert result["extracted_info"]["Scoring status"] == "Semester verified"


class _Doc:
    def __init__(self, status, kra, points, indicator_id, reviewer_score=None, public_id="doc"):
        self.status = status
        self.kra = kra
        self.points = points
        self.indicator_id = indicator_id
        self.reviewer_score = reviewer_score
        self.public_id = public_id
        self.deleted_at = None
        self.extracted_info = {}


def test_only_verified_scores_are_credited():
    auto_scored_pending = _Doc(
        "pendingReview",
        "instruction",
        0,
        "kra1-b-textbook-sole",
        public_id="pending",
    )
    auto_scored_pending.extracted_info = {
        "Simulation eligible": "yes",
        "System-calculated score": "32",
        "Provisional score": "32",
    }
    auto_scored_pending.simulation_points = 32
    summary = summarize_documents(
        [
            auto_scored_pending,
            _Doc("needsRevision", "instruction", 10, "kra1-b-module-sole", public_id="revision"),
            _Doc("rejected", "research", 50, "kra2-a-journal-sole", public_id="rejected"),
            _Doc("invalid", "research", 50, "kra2-a-book-sole", public_id="invalid"),
            _Doc("system_approved", "instruction", 20, "kra1-b-module-sole", public_id="system"),
            _Doc("validated", "research", 8, "kra2-a-journal-sole", reviewer_score=12, public_id="reviewed"),
        ],
        {"targets": {}, "criteria": {}, "indicators": {}, "rankWeights": {}},
        "Instructor I",
    )
    assert summary["totals"]["instruction"] == 30  # auto-scored pending (capped); system-approved needs full config snapshot
    assert summary["totals"]["research"] == 12
    assert summary["includesPending"] is True
