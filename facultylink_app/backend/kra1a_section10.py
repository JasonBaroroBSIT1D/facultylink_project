"""Section 10 — special evaluation-period circumstances (JC No. 01, s. 2026)."""

from __future__ import annotations

from kra1a_evaluation import STANDARD_REQUIRED_SEMESTERS

# Reviewer-verified exception codes; each adjusts required semester count when evidence is on file.
SECTION_10_EXCEPTIONS: dict[str, dict] = {
    "newly_appointed": {
        "label": "Newly appointed faculty",
        "requiredSemesters": None,  # computed from appointment date when provided
        "requiresReviewerVerification": True,
        "evidenceHint": "Appointment order and first semester of service.",
    },
    "study_leave": {
        "label": "Official study leave",
        "requiredSemesters": None,
        "requiresReviewerVerification": True,
        "evidenceHint": "Approved study-leave documentation covering the absent semesters.",
    },
    "maternity_leave": {
        "label": "Approved maternity leave",
        "requiredSemesters": None,
        "requiresReviewerVerification": True,
        "evidenceHint": "Approved maternity leave and return-to-service records.",
    },
    "sabbatical_leave": {
        "label": "Sabbatical leave",
        "requiredSemesters": None,
        "requiresReviewerVerification": True,
        "evidenceHint": "Sabbatical approval and service timeline.",
    },
    "suc_laboratory_school": {
        "label": "SUC laboratory school faculty",
        "requiredSemesters": None,
        "requiresReviewerVerification": True,
        "evidenceHint": "Laboratory school assignment and applicable evaluation policy.",
    },
}


def required_semesters_for_period(
    *,
    default: int = STANDARD_REQUIRED_SEMESTERS,
    exception_code: str | None = None,
    exception_verified: bool = False,
    eligible_semester_count: int | None = None,
) -> int:
    """Return how many semesters must be present before a regular-cycle average is finalized."""
    if not exception_code or not exception_verified:
        return default
    if exception_code not in SECTION_10_EXCEPTIONS:
        return default
    if eligible_semester_count is not None and eligible_semester_count > 0:
        return eligible_semester_count
    return default


def section10_catalog() -> list[dict]:
    return [
        {"code": code, **meta}
        for code, meta in SECTION_10_EXCEPTIONS.items()
    ]
