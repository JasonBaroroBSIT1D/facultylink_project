"""Soft delete, replacement eligibility, and submission version history."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTECTED_STATUSES = frozenset({"validated", "approved", "system_approved"})


def metadata_correction_block_reason(row: dict | Any | None) -> str | None:
    """Return a user-facing reason when extracted metadata may not be corrected."""
    if not row:
        return None
    status = row.get("status") if isinstance(row, dict) else getattr(row, "status", None)
    decided = row.get("decided_at") if isinstance(row, dict) else getattr(row, "decided_at", None)
    if status in PROTECTED_STATUSES:
        return (
            "This document already has a final decision. Reopen it before correcting extracted information."
        )
    if decided:
        return (
            "This document already has a final decision. Reopen it before correcting extracted information."
        )
    return None


DELETABLE_STATUSES = frozenset(
    {"pendingReview", "processing", "needsRevision", "rejected", "invalid", "pending-review"}
)
REPLACEABLE_STATUSES = frozenset(
    {"pendingReview", "processing", "needsRevision", "rejected", "invalid", "pending-review"}
)


def _has_reviewer_decision(doc) -> bool:
    return bool(
        getattr(doc, "decided_at", None)
        or getattr(doc, "review_snapshot", None)
        or getattr(doc, "reviewer_score", None) is not None
    )


def _credited(doc) -> bool:
    status = getattr(doc, "status", "") or ""
    if status in PROTECTED_STATUSES:
        return True
    points = getattr(doc, "points", 0) or 0
    return points > 0 and status == "system_approved"


def is_active(doc) -> bool:
    return getattr(doc, "deleted_at", None) is None


def faculty_may_delete(doc) -> tuple[bool, str]:
    if not is_active(doc):
        return False, "This document was already removed."
    if _has_reviewer_decision(doc):
        return False, "Documents with a reviewer decision cannot be deleted. Request withdrawal for approved records."
    if _credited(doc):
        return False, "Credited documents cannot be deleted without authorized withdrawal."
    status = getattr(doc, "status", "") or ""
    if status in PROTECTED_STATUSES:
        return False, "Approved documents require an authorized withdrawal request."
    if status not in DELETABLE_STATUSES:
        return False, "This document status does not allow deletion."
    return True, ""


def faculty_may_replace(doc) -> tuple[bool, str]:
    if not is_active(doc):
        return False, "This document was removed."
    if _has_reviewer_decision(doc):
        return False, "A reviewer decision is recorded. Wait for revision or reopening before replacing the file."
    if _credited(doc):
        return False, "Credited documents cannot be replaced without authorized withdrawal."
    status = getattr(doc, "status", "") or ""
    if status in PROTECTED_STATUSES:
        return False, "Approved documents cannot be replaced. Request withdrawal first."
    if status not in REPLACEABLE_STATUSES:
        return False, "Only pending or revision-requested documents can be replaced."
    return True, ""


def faculty_may_request_withdrawal(doc) -> tuple[bool, str]:
    if not is_active(doc):
        return False, "Document not found."
    status = getattr(doc, "status", "") or ""
    if status not in PROTECTED_STATUSES and not _credited(doc):
        return False, "Withdrawal applies only to approved or credited documents."
    return True, ""


def document_action_flags(doc) -> dict[str, bool]:
    may_delete, _ = faculty_may_delete(doc)
    may_replace, _ = faculty_may_replace(doc)
    may_withdraw, _ = faculty_may_request_withdrawal(doc)
    return {
        "canDelete": may_delete,
        "canReplace": may_replace,
        "canRequestWithdrawal": may_withdraw,
    }


def _history_list(info: dict | None) -> list[dict]:
    info = info or {}
    raw = info.get("Submission history") or "[]"
    if isinstance(raw, list):
        return list(raw)
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def append_submission_history(info: dict | None, entry: dict[str, Any]) -> dict[str, str]:
    history = _history_list(info)
    history.append(entry)
    return {"Submission history": json.dumps(history[-20:], ensure_ascii=False)}


def archive_upload_file(source: Path, upload_dir: Path, public_id: str, version: int) -> str | None:
    if not source.is_file():
        return None
    archive_dir = upload_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / f"{public_id}_v{version}_{source.name}"
    shutil.copy2(source, target)
    return str(target.resolve())


def utcnow():
    return datetime.now(timezone.utc)
