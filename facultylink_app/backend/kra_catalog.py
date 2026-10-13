"""Annex I KRA/criterion/indicator catalog for upload organization (structure only)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / "kra_catalog.json"

MOBILE_TO_WEB = {
    "instruction": "kra1",
    "research": "kra2",
    "extension": "kra3",
    "professionalDevelopment": "kra4",
}

WEB_TO_MOBILE = {v: k for k, v in MOBILE_TO_WEB.items()}


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        return {"kras": []}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_for_api() -> dict:
    return load_catalog()


def find_indicator(indicator_id: str | None) -> dict | None:
    if not indicator_id:
        return None
    for kra in load_catalog().get("kras") or []:
        for criterion in kra.get("criteria") or []:
            for indicator in criterion.get("indicators") or []:
                if indicator.get("id") == indicator_id:
                    return {
                        "kra": kra,
                        "criterion": criterion,
                        "indicator": indicator,
                        "mobileKey": kra.get("mobileKey"),
                    }
    return None


def find_criterion(criterion_id: str | None) -> dict | None:
    if not criterion_id:
        return None
    for kra in load_catalog().get("kras") or []:
        for criterion in kra.get("criteria") or []:
            if criterion.get("id") == criterion_id:
                return {"kra": kra, "criterion": criterion, "mobileKey": kra.get("mobileKey")}
    return None


def validate_selection(*, kra: str, criterion_id: str | None, indicator_id: str | None) -> tuple[bool, str]:
    """Ensure selected criterion/indicator belong to the selected mobile KRA key."""
    web_kra = MOBILE_TO_WEB.get(kra)
    if not web_kra:
        return False, "Select a valid Key Result Area."
    if indicator_id:
        found = find_indicator(indicator_id)
        if not found:
            return False, "The selected indicator was not found in the KRA catalog."
        if found["kra"]["id"] != web_kra:
            return False, "The selected indicator does not belong to the chosen KRA."
        return True, ""
    if criterion_id:
        found = find_criterion(criterion_id)
        if not found:
            return False, "The selected criterion was not found in the KRA catalog."
        if found["kra"]["id"] != web_kra:
            return False, "The selected criterion does not belong to the chosen KRA."
        return True, ""
    return False, "Select a criterion or indicator under the chosen KRA."


def criterion_for_indicator(indicator_id: str | None) -> str | None:
    found = find_indicator(indicator_id)
    if not found:
        return None
    return found["criterion"]["id"]
