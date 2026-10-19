"""Web backend shim — shared credential email lives in the mobile backend."""

from __future__ import annotations

import sys
from pathlib import Path

MOBILE_BACKEND = Path(__file__).resolve().parents[2] / "facultylink_app" / "backend"
if str(MOBILE_BACKEND) not in sys.path:
    sys.path.insert(0, str(MOBILE_BACKEND))

import account_credentials as _shared  # noqa: E402
from password_reset import EmailDeliveryError, EmailNotConfigured, password_problem, send_email  # noqa: E402

SUBJECT = _shared.REVIEWER_SUBJECT
SMTP_KEYS = _shared.SMTP_KEYS


def smtp_settings() -> dict:
    web_env = Path(__file__).resolve().parent / ".env"
    return _shared.smtp_settings(web_env=web_env)


choose_password = _shared.choose_password
reviewer_credential_message = _shared.reviewer_credential_message
deliver_reviewer_credentials = _shared.deliver_reviewer_credentials
deliver_faculty_credentials = _shared.deliver_faculty_credentials


def email_failure_message(error, *, account_created: bool) -> str:
    return _shared.email_failure_message(error, account_created=account_created, role="reviewer")


def faculty_email_failure_message(error, *, account_created: bool) -> str:
    return _shared.email_failure_message(error, account_created=account_created, role="faculty")
