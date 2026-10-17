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


@lru_cache(maxsize=1)
def load_indicator_rules() -> dict[str, dict]:
    if not RULES_PATH.exists():
        return {}
    text = RULES_PATH.read_text(encoding="utf-8")
    matches = list(_ID.finditer(text))
    rules: dict[str, dict] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else match.end() + 900
        block = text[match.end() : min(end, match.end() + 900)]
        indicator_id = match.group(1)
        points = _POINTS.search(block)
        maximum = _MAX.search(block)
        contribution = _CONTRIB.search(block)
        multiplier = _MULT.search(block)
        group = _GROUP.search(block)
        max_points = float(maximum.group(1)) if maximum else None
        rules[indicator_id] = {
            "id": indicator_id,
            "points": float(points.group(1)) if points else None,
            "maxPoints": max_points,
            "contribution": contribution.group(1) if contribution else "sole",
            "multiplier": float(multiplier.group(1)) if multiplier else None,
            "group": group.group(1) if group else None,
            "groupMax": float(group.group(2)) if group else None,
        }
    return rules


def rule_for(indicator_id: str | None) -> dict | None:
    if not indicator_id:
        return None
    return load_indicator_rules().get(indicator_id)
