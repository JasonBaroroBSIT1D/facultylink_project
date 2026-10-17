"""Load published KRA configuration from the shared Postgres kra_settings table.

The web admin backend owns create/update/publish. This mobile backend only reads
the active published row (id = 1) so Rank Simulation uses the same rules.
"""

from __future__ import annotations

import json
import re

from sqlalchemy import inspect, text

# Web rules.js KRA ids → mobile kra keys used in documents / kra_scores.
WEB_TO_MOBILE_KRA = {
    "kra1": "instruction",
    "kra2": "research",
    "kra3": "extension",
    "kra4": "professionalDevelopment",
}

MOBILE_TO_WEB_KRA = {v: k for k, v in WEB_TO_MOBILE_KRA.items()}

KRA_KEYS = (
    "instruction",
    "research",
    "extension",
    "professionalDevelopment",
)

# JC No. 01, s. 2026 defaults when published overrides are empty (matches web rules.js).
DEFAULT_KRA_MAX = {
    "instruction": 100,
    "research": 100,
    "extension": 100,
    "professionalDevelopment": 100,
}

# DBM–CHED Joint Circular Table 2.2 — KRA weights (%) by faculty rank band.
DEFAULT_RANK_WEIGHTS = {
    "Instructor": {
        "instruction": 60,
        "research": 10,
        "extension": 20,
        "professionalDevelopment": 10,
    },
    "Asst. Professor": {
        "instruction": 50,
        "research": 20,
        "extension": 20,
        "professionalDevelopment": 10,
    },
    "Assoc. Professor": {
        "instruction": 40,
        "research": 30,
        "extension": 20,
        "professionalDevelopment": 10,
    },
    "Professor": {
        "instruction": 30,
        "research": 40,
        "extension": 20,
        "professionalDevelopment": 10,
    },
    "College/University Professor": {
        "instruction": 20,
        "research": 50,
        "extension": 20,
        "professionalDevelopment": 10,
    },
}

SCORING_FORMULA = "Final Score = Base Points × Contribution Percentage"
WEIGHTED_FORMULA = (
    "Weighted Final Score = Σ (KRA points × Table 2.2 rank weight %)"
)


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


def normalize_rank_weights(raw) -> dict:
    """Return Table 2.2-style band → {mobile kra: percent} map."""
    if not isinstance(raw, dict) or not raw:
        return {band: dict(weights) for band, weights in DEFAULT_RANK_WEIGHTS.items()}

    normalized = {}
    for band, values in raw.items():
        if not isinstance(band, str) or not band.strip():
            continue
        if not isinstance(values, dict):
            continue
        entry = {}
        for key, value in values.items():
            mobile = WEB_TO_MOBILE_KRA.get(str(key), str(key))
            if mobile not in KRA_KEYS:
                continue
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number < 0 or number > 100:
                continue
            entry[mobile] = number
        if len(entry) == len(KRA_KEYS):
            # Accept percent totals near 100 (floating point / rounding).
            total = sum(entry.values())
            if 99.0 <= total <= 101.0:
                normalized[band.strip()] = entry
    return normalized or {
        band: dict(weights) for band, weights in DEFAULT_RANK_WEIGHTS.items()
    }


def resolve_rank_band(current_rank: str | None) -> str:
    """Map a faculty rank label to a Table 2.2 band name."""
    text_value = (current_rank or "").strip().lower()
    if not text_value:
        return "Instructor"
    compact = re.sub(r"[^a-z0-9]+", " ", text_value)
    if "college" in compact or "university professor" in compact or "col univ" in compact:
        return "College/University Professor"
    if "assoc" in compact:
        return "Assoc. Professor"
    if "asst" in compact or "assistant" in compact:
        return "Asst. Professor"
    if "professor" in compact:
        return "Professor"
    return "Instructor"


def weights_for_rank(config: dict, current_rank: str | None) -> tuple[str, dict]:
    """Return (band name, per-KRA weight percents) for the faculty rank."""
    weights = normalize_rank_weights(config.get("rankWeights"))
    band = resolve_rank_band(current_rank)
    if band in weights:
        return band, dict(weights[band])
    # Fuzzy match published keys.
    band_l = band.lower()
    for key, value in weights.items():
        if key.lower() == band_l or band_l in key.lower() or key.lower() in band_l:
            return key, dict(value)
    return band, dict(DEFAULT_RANK_WEIGHTS[band])


def weighted_final_score(kra_points: dict, weights_percent: dict) -> float:
    """Table 2.2: Σ (KRA points × weight%). KRA points are 0–100 scale."""
    total = 0.0
    for kra in KRA_KEYS:
        points = float(kra_points.get(kra, 0) or 0)
        weight = float(weights_percent.get(kra, 0) or 0) / 100.0
        total += points * weight
    return round(total, 2)


def _empty_config() -> dict:
    return {
        "version": 0,
        "status": "default",
        "publishedAt": "",
        "formula": SCORING_FORMULA,
        "weightedFormula": WEIGHTED_FORMULA,
        "targets": dict(DEFAULT_KRA_MAX),
        "requiredPoints": 100,
        "kras": {},
        "criteria": {},
        "indicators": {},
        "rankWeights": {
            band: dict(weights) for band, weights in DEFAULT_RANK_WEIGHTS.items()
        },
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
    rank_weights = normalize_rank_weights(payload.get("rankWeights"))
    return {
        "version": version,
        "status": row.get("status") or "published",
        "publishedAt": row.get("published_at") or row.get("updated_at") or "",
        "formula": formula,
        "weightedFormula": WEIGHTED_FORMULA,
        "targets": targets,
        "requiredPoints": 100,
        "kras": payload.get("kras") or {},
        "criteria": criteria,
        "indicators": indicators,
        "rankWeights": rank_weights,
    }


def document_earned_points(doc, config: dict | None = None) -> float:
    """Prefer reviewer-awarded score (web formula result); fall back to stored points."""
    from indicator_rules import rule_for

    score = None
    if getattr(doc, "reviewer_score", None) is not None and getattr(doc, "status", None) in {
        "validated",
        "approved",
    }:
        try:
            score = float(doc.reviewer_score)
        except (TypeError, ValueError):
            score = None
    if score is None:
        try:
            score = float(doc.points or 0)
        except (TypeError, ValueError):
            score = 0.0

    cap = indicator_cap(config or {}, getattr(doc, "indicator_id", None)) if config else None
    rule = rule_for(getattr(doc, "indicator_id", None))
    if rule and isinstance(rule.get("maxPoints"), (int, float)):
        rule_cap = float(rule["maxPoints"])
        cap = rule_cap if cap is None else min(cap, rule_cap)
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


def final_score(base_points: float, contribution_percent: float) -> float:
    """Same formula as web: Final Score = Base Points × Contribution Percentage."""
    return round(float(base_points) * (float(contribution_percent) / 100.0), 2)
