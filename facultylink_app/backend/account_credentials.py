"""Shared temporary-password email delivery for faculty and reviewer accounts."""

from __future__ import annotations

from pathlib import Path

from password_reset import (
    EmailDeliveryError,
    EmailNotConfigured,
    password_problem,
    send_email,
)

BACKEND_DIR = Path(__file__).resolve().parent
SMTP_KEYS = (
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_SECURITY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_FROM",
)

REVIEWER_SUBJECT = "Your FacultyLink reviewer account"
FACULTY_SUBJECT = "Your FacultyLink faculty account"


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


def smtp_settings(*, web_env: Path | None = None) -> dict:
    """Load SMTP from ``facultylink_app/backend/.env`` (source of truth).

    Optional ``web_env`` and process environment override individual keys.
    ``SMTP_FROM`` falls back to ``SMTP_USERNAME``, matching ``Config``.
    """
    merged = read_env_file(BACKEND_DIR / ".env")
    if web_env is not None:
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


def smtp_settings_from_flask(app_config) -> dict:
    """Build the same dict shape from a Flask ``app.config`` (mobile API)."""
    sender = (app_config.get("SMTP_FROM") or app_config.get("SMTP_USERNAME") or "").strip()
    return {
        "SMTP_HOST": (app_config.get("SMTP_HOST") or "").strip(),
        "SMTP_PORT": app_config.get("SMTP_PORT") or 587,
        "SMTP_SECURITY": (app_config.get("SMTP_SECURITY") or "starttls").strip().lower(),
        "SMTP_USERNAME": (app_config.get("SMTP_USERNAME") or "").strip(),
        "SMTP_PASSWORD": app_config.get("SMTP_PASSWORD") or "",
        "SMTP_FROM": sender,
    }


def choose_password(supplied, generator) -> tuple[str | None, str | None]:
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


def faculty_credential_message(name: str, email: str, password: str) -> str:
    return (
        "FacultyLink account\n\n"
        f"A faculty account was created for {name}.\n\n"
        f"Login email: {email}\n"
        f"Temporary password: {password}\n\n"
        "Sign in to the FacultyLink mobile app with this email and temporary password.\n"
        "On your first login, change this temporary password before uploading documents "
        "or viewing your assessment.\n\n"
        "If you did not expect this account, contact your institution administrator."
    )


def deliver_reviewer_credentials(config, name: str, email: str, password: str, portal_url: str) -> None:
    send_email(
        config,
        email,
        REVIEWER_SUBJECT,
        reviewer_credential_message(name, email, password, portal_url),
    )


def deliver_faculty_credentials(config, name: str, email: str, password: str) -> None:
    send_email(
        config,
        email,
        FACULTY_SUBJECT,
        faculty_credential_message(name, email, password),
    )


def email_failure_message(error, *, account_created: bool, role: str) -> str:
    if isinstance(error, EmailNotConfigured):
        lead = "Email delivery is not configured. Missing: " + ", ".join(error.missing) + "."
    elif isinstance(error, EmailDeliveryError):
        lead = "The credential email could not be delivered."
    else:
        lead = "The credential email could not be delivered."
    resend = "Resend credentials" if role == "reviewer" else "Resend credentials"
    if account_created:
        return (
            lead
            + f" The {role} account was created, but the temporary password was not kept. "
            + f"Use {resend} to issue a new password."
        )
    return lead + " The current password was not changed."


__all__ = [
    "EmailDeliveryError",
    "EmailNotConfigured",
    "choose_password",
    "deliver_faculty_credentials",
    "deliver_reviewer_credentials",
    "email_failure_message",
    "faculty_credential_message",
    "password_problem",
    "reviewer_credential_message",
    "smtp_settings",
    "smtp_settings_from_flask",
]
