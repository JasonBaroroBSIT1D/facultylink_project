"""Load published KRA configuration from the shared Postgres kra_settings table.

The web admin backend owns create/update/publish. This mobile backend only reads
the active published row (id = 1) so Rank Simulation uses the same rules.
"""

from __future__ import annotations

import json

from sqlalchemy import inspect, text

# Web rules.js KRA ids → mobile kra keys used in documents / kra_scores.
WEB_TO_MOBILE_KRA = {
    "kra1": "instruction",
    "kra2": "research",
    "kra3": "extension",
    "kra4": "professionalDevelopment",
}

# Annex I defaults when published overrides are empty (matches web rules.js).
DEFAULT_KRA_MAX = {
    "instruction": 100,
    "research": 100,
    "extension": 100,
    "professionalDevelopment": 100,
}

SCORING_FORMULA = "Final Score = Base Points × Contribution Percentage"


def _parse_payload(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _empty_config() -> dict:
    return {
        "version": 0,
        "status": "default",
        "publishedAt": "",
        "formula": SCORING_FORMULA,
        "targets": dict(DEFAULT_KRA_MAX),
        "requiredPoints": sum(DEFAULT_KRA_MAX.values()),
        "kras": {},
        "criteria": {},
        "indicators": {},
        "rankWeights": {},
    }


def load_active_kra_config(db) -> dict:
    """Return the active published KRA configuration from kra_settings id=1."""
    try:
        if not inspect(db.engine).has_table("kra_settings"):
            return _empty_config()
    except Exception:
        db.session.rollback()
        return _empty_config()

    try:
        row = db.session.execute(
            text(
                """
                SELECT payload, version, status, published_at, formula, updated_at
                FROM kra_settings
                WHERE id = 1
                LIMIT 1
                """
            )
        ).mappings().first()
    except Exception:
        db.session.rollback()
        return _empty_config()

    if not row:
        return _empty_config()

    payload = _parse_payload(row.get("payload"))
    version = int(row.get("version") or 1)
    formula = (row.get("formula") or "").strip() or SCORING_FORMULA
    targets = dict(DEFAULT_KRA_MAX)
    for web_id, mobile_id in WEB_TO_MOBILE_KRA.items():
        entry = (payload.get("kras") or {}).get(web_id) or {}
        if isinstance(entry, dict) and isinstance(entry.get("maxPoints"), (int, float)):
            targets[mobile_id] = int(round(float(entry["maxPoints"])))

    indicators = payload.get("indicators") if isinstance(payload.get("indicators"), dict) else {}
    criteria = payload.get("criteria") if isinstance(payload.get("criteria"), dict) else {}
    rank_weights = payload.get("rankWeights") if isinstance(payload.get("rankWeights"), dict) else {}
    return {
        "version": version,
        "status": row.get("status") or "published",
        "publishedAt": row.get("published_at") or row.get("updated_at") or "",
        "formula": formula,
        "targets": targets,
        "requiredPoints": sum(targets.values()),
        "kras": payload.get("kras") or {},
        "criteria": criteria,
        "indicators": indicators,
        "rankWeights": rank_weights,
    }


def document_earned_points(doc, config: dict | None = None) -> float:
    """Prefer reviewer-awarded score (web formula result); fall back to stored points."""
    score = None
    if getattr(doc, "reviewer_score", None) is not None:
        try:
            score = float(doc.reviewer_score)
        except (TypeError, ValueError):
            score = None
    if score is None:
        try:
            score = float(doc.points or 0)
        except (TypeError, ValueError):
            score = 0.0

    if config:
        cap = indicator_cap(config, getattr(doc, "indicator_id", None))
        if cap is not None:
            score = min(score, cap)
    return score


def indicator_cap(config: dict, indicator_id: str | None) -> float | None:
    if not indicator_id:
        return None
    entry = (config.get("indicators") or {}).get(indicator_id) or {}
    if isinstance(entry.get("maxPoints"), (int, float)):
        return float(entry["maxPoints"])
    return None


def rank_weight_factor(config: dict, current_rank: str | None) -> float:
    """Optional faculty-rank weight from published config; default 1.0."""
    weights = config.get("rankWeights") or {}
    if not weights or not current_rank:
        return 1.0
    value = weights.get(current_rank) or weights.get(current_rank.lower())
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return 1.0


def final_score(base_points: float, contribution_percent: float) -> float:
    """Same formula as web: Final Score = Base Points × Contribution Percentage."""
    return round(float(base_points) * (float(contribution_percent) / 100.0), 2)
