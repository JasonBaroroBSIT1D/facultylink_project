"""Shared evaluation schedule helpers for the faculty API.

The web admin UI writes `evaluation_periods`. The mobile app historically
read `preparation_periods`. These helpers treat the published web schedule
as the source of truth and keep both tables aligned.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import inspect, text

PERIOD_ID = "evaluation"
PERIOD_LABEL = "Rank Upgrade and Reclassification"


def compute_period_status(start: date, end: date, today: date | None = None) -> str:
    today = today or date.today()
    if today > end:
        return "closed"
    if today < start:
        return "open"
    if (end - today).days <= 14:
        return "closingSoon"
    return "open"


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def evaluation_period_row(db) -> dict | None:
    """Return the published faculty-visible evaluation schedule, if any."""
    if not inspect(db.engine).has_table("evaluation_periods"):
        return None
    row = db.session.execute(
        text(
            """
            SELECT id, start_date, end_date, published, visibility
            FROM evaluation_periods
            WHERE id = :id
            LIMIT 1
            """
        ),
        {"id": PERIOD_ID},
    ).mappings().first()
    if not row:
        return None

    visibility = (row.get("visibility") or "").strip().lower()
    if visibility in {"reviewers", "faculty"}:
        visibility = "all"
    published = bool(row.get("published")) or visibility == "all"
    if visibility == "draft" or not published:
        return None

    start = _parse_iso_date(row.get("start_date"))
    end = _parse_iso_date(row.get("end_date"))
    if not start or not end:
        return None

    status = compute_period_status(start, end)
    return {
        "cycleName": PERIOD_LABEL,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "reviewerAvailableUntil": end.isoformat(),
        "status": status,
        "start": start,
        "end": end,
    }


def preparation_period_payload(db, fallback_period) -> dict | None:
    """Payload for `/api/preparation-period` and dashboard."""
    published = evaluation_period_row(db)
    if published:
        return {
            "cycleName": published["cycleName"],
            "startDate": published["startDate"],
            "endDate": published["endDate"],
            "reviewerAvailableUntil": published["reviewerAvailableUntil"],
            "status": published["status"],
        }
    if fallback_period is None:
        return None
    return fallback_period.to_dict()

