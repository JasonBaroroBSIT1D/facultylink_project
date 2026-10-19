"""Reviewer sign-in credentials.

Password rules and SMTP delivery come from the shared password-reset
service. This module does not store or log the plaintext password.
"""

from __future__ import annotations

import sys
from pathlib import Path

MOBILE_BACKEND = Path(__file__).resolve().parents[2] / "facultylink_app" / "backend"
if str(MOBILE_BACKEND) not in sys.path:
    sys.path.insert(0, str(MOBILE_BACKEND))

from password_reset import (  # noqa: E402
    EmailDeliveryError,
    EmailNotConfigured,
    password_problem,
    send_email,
)

SUBJECT = "Your FacultyLink reviewer account"
SMTP_KEYS = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_SECURITY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM",
)


def read_env_file(path: Path) -> dict:
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def smtp_settings() -> dict:
    """SMTP settings shared with the mobile password-reset service.

    The mobile backend ``.env`` is the source of truth. A web ``.env``
    value, then the process environment, overrides a single key when set.
    ``SMTP_FROM`` falls back to ``SMTP_USERNAME``, matching the mobile app.
    """
    merged = read_env_file(MOBILE_BACKEND / ".env")
    web_env = Path(__file__).resolve().parent / ".env"
    for key, value in read_env_file(web_env).items():
        if value:
            merged[key] = value
    import os

    for key in SMTP_KEYS:
        if os.environ.get(key):
            merged[key] = os.environ[key]
    sender = (merged.get("SMTP_FROM") or merged.get("SMTP_USERNAME") or "").strip()
    return {
        "SMTP_HOST": (merged.get("SMTP_HOST") or "").strip(),
        "SMTP_PORT": merged.get("SMTP_PORT") or 587,
        "SMTP_SECURITY": (merged.get("SMTP_SECURITY") or "starttls").strip().lower(),
        "SMTP_USERNAME": (merged.get("SMTP_USERNAME") or "").strip(),
        "SMTP_PASSWORD": merged.get("SMTP_PASSWORD") or "",
        "SMTP_FROM": sender,
    }


def choose_password(supplied, generator) -> tuple[str | None, str | None]:
    """Use the administrator's password, or generate one that passes the shared rules."""
    value = str(supplied or "").strip()
    if value:
        problem = password_problem(value)
        if problem:
            return None, problem
        return value, None
    for _ in range(8):
        generated = generator()
        if password_problem(generated) is None:
            return generated, None
    return None, "A temporary password could not be generated."


def reviewer_credential_message(name: str, email: str, password: str, portal_url: str) -> str:
    portal = portal_url or "the FacultyLink Web Portal"
    return (
        "FacultyLink account\n\n"
        f"A reviewer account was created for {name}.\n\n"
        f"Login email: {email}\n"
        f"Temporary password: {password}\n\n"
        f"Sign in to the FacultyLink Web Portal at {portal} with this email and temporary password.\n"
        "On your first login, change this temporary password before using reviewer pages.\n"
        "FacultyLink will not open assigned documents until the password is changed.\n\n"
        "If you did not expect this account, contact your institution administrator."
    )


def deliver_reviewer_credentials(config, name: str, email: str, password: str, portal_url: str) -> None:
    """Send the credential email. Raises EmailNotConfigured or EmailDeliveryError."""
    send_email(
        config,
        email,
        SUBJECT,
        reviewer_credential_message(name, email, password, portal_url),
    )


def email_failure_message(error, *, account_created: bool) -> str:
    if isinstance(error, EmailNotConfigured):
        lead = "Email delivery is not configured. Missing: " + ", ".join(error.missing) + "."
    elif isinstance(error, EmailDeliveryError):
        lead = "The credential email could not be delivered."
    else:
        lead = "The credential email could not be delivered."
    if account_created:
        return (
            lead
            + " The reviewer account was created, but the temporary password was not kept. "
            + "Use Resend credentials to issue a new password."
        )
    return lead + " The current password was not changed."
