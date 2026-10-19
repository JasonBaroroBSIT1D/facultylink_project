"""Email OTP password recovery helpers (stored on the existing ``users`` row)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

GENERIC_REQUEST_MESSAGE = (
    "If that email belongs to a FacultyLink account, a 6-digit code has been sent to it."
)
INVALID_CODE_MESSAGE = "The code is invalid or has expired. Request a new code."
INVALID_RESET_MESSAGE = "This password reset session is invalid or has expired. Start again."


class EmailNotConfigured(RuntimeError):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(
            "Email delivery is not configured. Missing: " + ", ".join(missing)
        )


class EmailDeliveryError(RuntimeError):
    pass


def utc_now() -> datetime:
    """Naive UTC, matching the timestamp-without-time-zone columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def missing_email_settings(config) -> list[str]:
    missing = []
    if not config.get("SMTP_HOST"):
        missing.append("SMTP_HOST")
    if not config.get("SMTP_FROM"):
        missing.append("SMTP_FROM (or SMTP_USERNAME)")
    if config.get("SMTP_USERNAME") and not config.get("SMTP_PASSWORD"):
        missing.append("SMTP_PASSWORD")
    return missing


def send_email(config, to_address: str, subject: str, body: str) -> None:
    """Send a plain-text email through the configured SMTP server."""
    missing = missing_email_settings(config)
    if missing:
        raise EmailNotConfigured(missing)

    message = EmailMessage()
    message["From"] = config["SMTP_FROM"]
    message["To"] = to_address
    message["Subject"] = subject
    message.set_content(body)

    host = config["SMTP_HOST"]
    port = int(config.get("SMTP_PORT") or 587)
    security = (config.get("SMTP_SECURITY") or "starttls").lower()
    try:
        if security == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=15)
        with server:
            if security == "starttls":
                server.starttls(context=ssl.create_default_context())
            if config.get("SMTP_USERNAME"):
                server.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        raise EmailDeliveryError(str(error)) from error


def _digest(secret_key: str, purpose: str, email: str, value: str) -> str:
    message = f"{purpose}:{email.lower()}:{value}".encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(secret_key: str, email: str, otp: str) -> str:
    return _digest(secret_key, "otp", email, otp)


def hash_reset_token(secret_key: str, email: str, token: str) -> str:
    return _digest(secret_key, "reset", email, token)


def matches(expected_hash: str | None, candidate_hash: str) -> bool:
    return bool(expected_hash) and hmac.compare_digest(expected_hash, candidate_hash)


def otp_email_body(otp: str, ttl_seconds: int) -> str:
    minutes = max(ttl_seconds // 60, 1)
    return (
        "FacultyLink password reset\n\n"
        f"Your verification code is: {otp}\n\n"
        f"The code expires in {minutes} minutes and can be used once.\n"
        "If you did not request this, you can ignore this email. "
        "Your password has not been changed."
    )


def password_problem(password: str | None) -> str | None:
    value = password or ""
    if len(value) < PASSWORD_MIN_LENGTH:
        return f"Use at least {PASSWORD_MIN_LENGTH} characters."
    if len(value) > PASSWORD_MAX_LENGTH:
        return f"Use at most {PASSWORD_MAX_LENGTH} characters."
    return None


def seconds_until(moment: datetime | None, now: datetime) -> int:
    if not moment:
        return 0
    return max(int((moment - now).total_seconds() + 0.999), 0)


def add_seconds(now: datetime, seconds: int) -> datetime:
    return now + timedelta(seconds=seconds)
