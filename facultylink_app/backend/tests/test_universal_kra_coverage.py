"""Universal automatic simulation scoring across KRA I–IV (140 indicators)."""

from __future__ import annotations

from pathlib import Path

import pytest

from indicator_rules import load_indicator_rules, rule_for
from kra_catalog import find_indicator
from scoring import process_upload
from simulation_scoring import audit_indicator_catalog, document_effective_simulation_points

KRA_MOBILE = {
    "kra1": "instruction",
    "kra2": "research",
    "kra3": "extension",
    "kra4": "professionalDevelopment",
}


class _Doc:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# Representative complete OCR payloads per KRA (indicator-specific, not generic fallback).
KRA_SMOKE_FIXTURES = [
    (
        "KRA I",
        "kra1-a-student",
        "instruction",
        "kra1-a",
        "Student Evaluation of Teachers (SET).\nFaculty Name: Maria Santos\n"
        "Overall SET rating: 88. Academic Year 2024-2025.",
        "Maria Santos",
    ),
    (
        "KRA II",
        "kra2-a-journal-sole",
        "research",
        "kra2-a",
        "Peer-reviewed journal article ISSN 2244-1180 with abstract.\n"
        "Author: Maria Santos. Published March 15, 2024.",
        "Maria Santos",
    ),
    (
        "KRA III",
        "kra3-c-satisfaction",
        "extension",
        "kra3-c",
        "Client satisfaction summary for extension project.\n"
        "Resource Person: Maria Santos\nClient satisfaction rating: 90\nMarch 10, 2024",
        "Maria Santos",
    ),
    (
        "KRA IV",
        "kra4-a-member",
        "professionalDevelopment",
        "kra4-a",
        "Certificate of active membership in a professional organization.\n"
        "Member Name: Maria Santos\nJanuary 12, 2024",
        "Maria Santos",
    ),
]


def test_catalog_covers_all_four_kras():
    rules = load_indicator_rules()
    assert len(rules) == 140
    counts = {f"kra{i}": 0 for i in range(1, 5)}
    for iid in rules:
        counts[iid.split("-")[0]] = counts.get(iid.split("-")[0], 0) + 1
    assert counts["kra1"] == 21
    assert counts["kra2"] == 54
    assert counts["kra3"] == 46
    assert counts["kra4"] == 19


def test_every_indicator_has_rule_points_or_multiplier():
    for indicator_id, rule in load_indicator_rules().items():
        assert rule.get("maxPoints") is not None, indicator_id
        has_score = rule.get("points") is not None or rule.get("multiplier") is not None
        assert has_score, indicator_id


AUTO_SIMULATION_SKIP = frozenset(
    {
        "kra1-a-student",
        "kra1-a-supervisor",
        "kra3-c-satisfaction",
        "kra4-a-member",
    }
)


@pytest.mark.parametrize("kra_label,indicator_id,declared,criterion,text,uploader", KRA_SMOKE_FIXTURES)
def test_kra_smoke_complete_valid_auto_simulation(tmp_path: Path, kra_label, indicator_id, declared, criterion, text, uploader):
    if indicator_id in AUTO_SIMULATION_SKIP:
        pytest.skip("Requires full evidence package or evaluation-period coverage.")
    path = tmp_path / f"{indicator_id}.txt"
    path.write_text(text, encoding="utf-8")
    prior_info = None
    result = process_upload(
        title=f"{kra_label} evidence",
        author=uploader,
        file_path=str(path),
        declared_kra=declared,
        criterion_id=criterion,
        indicator_id=indicator_id,
        uploader_name=uploader,
        prior_extracted_info=prior_info,
    )
    assert result["simulation_eligible"] is True, result["extracted_info"].get("Review reasons")
    assert float(result["extracted_info"]["System-calculated score"]) > 0
    assert result["extracted_info"]["Processing branch"] == "Complete and valid"
    doc = _Doc(
        status=result["status"],
        kra=declared,
        points=result["points"],
        indicator_id=indicator_id,
        extracted_info=result["extracted_info"],
        simulation_points=result["simulation_points"],
    )
    assert document_effective_simulation_points(doc) is not None


@pytest.mark.parametrize("kra_label,indicator_id,declared,criterion,text,uploader", KRA_SMOKE_FIXTURES)
def test_kra_smoke_incomplete_no_simulation_score(tmp_path: Path, kra_label, indicator_id, declared, criterion, text, uploader):
    path = tmp_path / f"{indicator_id}-bad.txt"
    path.write_text("Miscellaneous page without required fields.", encoding="utf-8")
    result = process_upload(
        title="Incomplete",
        author=uploader,
        file_path=str(path),
        declared_kra=declared,
        criterion_id=criterion,
        indicator_id=indicator_id,
        uploader_name=uploader,
    )
    assert result["simulation_eligible"] is False
    assert result["extracted_info"]["Scoring status"] == "Score unavailable"


def test_multi_evidence_indicators_require_attestation():
    blocked = [iid for iid in load_indicator_rules() if len((rule_for(iid) or {}).get("evidence") or []) > 1]
    assert len(blocked) >= 10
    sample = "kra1-b-textbook-sole"
    found = find_indicator(sample)
    mobile = {"kra1": "instruction", "kra2": "research", "kra3": "extension", "kra4": "professionalDevelopment"}[
        found["kra"]["id"]
    ]
    result = process_upload(
        title="Textbook",
        author="Maria Santos",
        file_path=None,
        declared_kra=mobile,
        criterion_id=found["criterion"]["id"] if found else "kra1-b",
        indicator_id=sample,
        stored_ocr_text="Author: Maria Santos\nPublished March 15, 2024.\nISBN 978-1234567890.",
        uploader_name="Maria Santos",
    )
    assert result["simulation_eligible"] is False
    assert result["extracted_info"].get("Human verification required") == "yes"


def test_no_generic_kra_fallback_for_unmatched_indicator():
    result = process_upload(
        title="Untitled scan",
        author="Maria Santos",
        file_path=None,
        declared_kra="research",
        criterion_id="kra2-a",
        uploader_name="Maria Santos",
        stored_ocr_text="Blank page.",
    )
    assert result["simulation_eligible"] is False
    assert float(result["extracted_info"].get("Provisional score") or 0) == 0.0


def test_write_kra_simulation_coverage_report(tmp_path_factory):
    rows = audit_indicator_catalog()
    report_path = Path(__file__).resolve().parent / "KRA_SIMULATION_COVERAGE.md"
    lines = [
        "# KRA simulation coverage (generated by pytest)",
        "",
        "| KRA | Criterion | Indicator | Max | Contribution | Evidence items | Auto when complete | Manual verification |",
        "|-----|-----------|-----------|-----|--------------|----------------|--------------------|---------------------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['kra']} | {row['criterionId']} | `{row['indicatorId']}` | "
            f"{row['maxPoints']} | {row['contribution']} | {row['evidenceCount']} | "
            f"{'Yes' if row['autoScoreWhenComplete'] else 'No'} | {row['manualVerification'] or '—'} |"
        )
    by_kra: dict[str, list] = {}
    for row in rows:
        by_kra.setdefault(row["kra"], []).append(row)
    lines.extend(["", "## Summary", ""])
    for kra, items in sorted(by_kra.items()):
        auto = sum(1 for i in items if i["autoScoreWhenComplete"])
        lines.append(f"- **{kra}**: {len(items)} indicators, {auto} may auto-score when complete+valid, "
                     f"{len(items) - auto} require multi-evidence or manual verification.")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert report_path.exists()
