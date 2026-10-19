"""Indicator point rules parsed from the web JC No. 01, s. 2026 rule set."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

RULES_PATH = (
    Path(__file__).resolve().parents[2]
    / "facultylink_web"
    / "assets"
    / "js"
    / "rules.js"
)

_ID = re.compile(r'\bid:\s*"(kra[1-4]-[a-z]-[a-z0-9-]+)"')
_POINTS = re.compile(r"\bpoints:\s*(-?\d+(?:\.\d+)?)")
_MAX = re.compile(r"\bmaxPoints:\s*(-?\d+(?:\.\d+)?)")
_CONTRIB = re.compile(r'\bcontribution:\s*"([^"]+)"')
_MULT = re.compile(r"\bmultiplier:\s*(\d+(?:\.\d+)?)")
_GROUP = re.compile(r'groupMax:\s*\{\s*group:\s*"([^"]+)"\s*,\s*max:\s*(\d+(?:\.\d+)?)')
_EVIDENCE = re.compile(r"evidence:\s*\[(.*?)\]", re.S)
_QUOTE = re.compile(r'"([^"]+)"')
_CRITERION = re.compile(
    r'id:\s*"(kra[1-4]-[a-d])"\s*,\s*name:\s*"[^"]+"\s*,\s*maxPoints:\s*(\d+(?:\.\d+)?)'
)
_KRA = re.compile(
    r'id:\s*"(kra[1-4])"\s*,\s*code:\s*"[^"]+"\s*,\s*name:\s*"[^"]+"\s*,\s*maxPoints:\s*(\d+(?:\.\d+)?)'
)
_BONUS_MAX = re.compile(r"\s*,\s*bonusMax:\s*(\d+(?:\.\d+)?)")


def _rules_text() -> str:
    if not RULES_PATH.exists():
        return ""
    return RULES_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_indicator_rules() -> dict[str, dict]:
    text = _rules_text()
    if not text:
        return {}
    matches = list(_ID.finditer(text))
    rules: dict[str, dict] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end() : end]
        indicator_id = match.group(1)
        points = _POINTS.search(block)
        maximum = _MAX.search(block)
        contribution = _CONTRIB.search(block)
        multiplier = _MULT.search(block)
        group = _GROUP.search(block)
        evidence_block = _EVIDENCE.search(block)
        evidence = _QUOTE.findall(evidence_block.group(1)) if evidence_block else []
        max_points = float(maximum.group(1)) if maximum else None
        rules[indicator_id] = {
            "id": indicator_id,
            "points": float(points.group(1)) if points else None,
            "maxPoints": max_points,
            "contribution": contribution.group(1) if contribution else "sole",
            "multiplier": float(multiplier.group(1)) if multiplier else None,
            "group": group.group(1) if group else None,
            "groupMax": float(group.group(2)) if group else None,
            "evidence": evidence,
        }
    return rules


@lru_cache(maxsize=1)
def load_scoring_structure() -> dict:
    """Criterion maxima, KRA maxima, and KRA III/IV bonus flags from Annex A."""
    text = _rules_text()
    kras: dict[str, dict] = {}
    for match in _KRA.finditer(text):
        bonus = _BONUS_MAX.match(text[match.end() : match.end() + 40])
        kras[match.group(1)] = {
            "maxPoints": float(match.group(2)),
            "bonusMax": float(bonus.group(1)) if bonus else 0.0,
        }
    criteria: dict[str, dict] = {}
    for match in _CRITERION.finditer(text):
        criterion_id = match.group(1)
        window = text[match.end() : match.end() + 40]
        criteria[criterion_id] = {
            "kra": criterion_id.rsplit("-", 1)[0],
            "maxPoints": float(match.group(2)),
            "bonus": "bonus: true" in window,
        }
    return {"kras": kras, "criteria": criteria}


def rule_for(indicator_id: str | None) -> dict | None:
    if not indicator_id:
        return None
    return load_indicator_rules().get(indicator_id)
