"""Shared faculty and reviewer credential email helpers."""

import secrets

import account_credentials
from password_reset import missing_email_settings


def test_faculty_and_reviewer_messages_include_first_login():
    faculty = account_credentials.faculty_credential_message(
        "Pat Cruz", "pat@example.edu", "temp-pass-12345678"
    )
    reviewer = account_credentials.reviewer_credential_message(
        "Pat Cruz", "pat@example.edu", "temp-pass-12345678", "http://127.0.0.1:8765/login.html"
    )
    assert "mobile app" in faculty
    assert "first login" in faculty
    assert "Web Portal" in reviewer
    assert "first login" in reviewer


def test_smtp_settings_match_mobile_env_keys():
    settings = account_credentials.smtp_settings()
    assert set(settings) >= set(account_credentials.SMTP_KEYS)
    missing = missing_email_settings(settings)
    assert isinstance(missing, list)


def test_live_gmail_delivery_for_both_workflows():
    """When Gmail SMTP is configured in backend/.env, both templates send successfully."""
    settings = account_credentials.smtp_settings()
    missing = missing_email_settings(settings)
    if missing:
        return
    recipient = settings["SMTP_FROM"]
    probe = "FL-" + secrets.token_urlsafe(6)
    account_credentials.deliver_faculty_credentials(settings, "FacultyLink Test", recipient, probe)
    account_credentials.deliver_reviewer_credentials(
        settings,
        "FacultyLink Test",
        recipient,
        probe,
        "http://127.0.0.1:8765/login.html",
    )
