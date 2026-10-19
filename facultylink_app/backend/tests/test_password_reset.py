import re
from datetime import timedelta

import pytest

import password_reset
from app import app, db
from models import User

EMAIL = "maria.santos@university.edu.ph"
OLD_PASSWORD = "password123"
NEW_PASSWORD = "NewSecret456"


@pytest.fixture()
def outbox(monkeypatch):
    """Configure fake SMTP settings and capture emails instead of sending them."""
    monkeypatch.setitem(app.config, "SMTP_HOST", "smtp.test")
    monkeypatch.setitem(app.config, "SMTP_FROM", "noreply@test")
    sent: list[dict] = []

    def fake_send(config, to_address, subject, body):
        sent.append({"to": to_address, "subject": subject, "body": body})

    monkeypatch.setattr(password_reset, "send_email", fake_send)
    return sent


def last_otp(outbox) -> str:
    return re.search(r"code is: (\d{6})", outbox[-1]["body"]).group(1)


def request_code(client, email=EMAIL):
    return client.post("/api/auth/forgot-password/request", json={"email": email})


def verify(client, otp, email=EMAIL):
    return client.post("/api/auth/forgot-password/verify", json={"email": email, "otp": otp})


def reset(client, token, password=NEW_PASSWORD, email=EMAIL):
    return client.post(
        "/api/auth/forgot-password/reset",
        json={"email": email, "resetToken": token, "newPassword": password},
    )


def login(client, password):
    return client.post("/api/auth/login", json={"email": EMAIL, "password": password})


def shift_user(**offsets):
    """Move stored reset timestamps into the past to simulate elapsed time."""
    with app.app_context():
        user = User.query.filter_by(email=EMAIL).first()
        for column, seconds in offsets.items():
            setattr(user, column, getattr(user, column) - timedelta(seconds=seconds))
        db.session.commit()


def test_request_reports_missing_email_configuration(client, monkeypatch):
    monkeypatch.setitem(app.config, "SMTP_HOST", "")
    monkeypatch.setitem(app.config, "SMTP_FROM", "")
    response = request_code(client)
    assert response.status_code == 503
    body = response.get_json()
    assert "SMTP_HOST" in body["missingConfig"]
    # Same answer for an unknown address, so nothing is revealed about accounts.
    assert request_code(client, "nobody@example.com").status_code == 503


def test_full_recovery_flow_updates_password(client, outbox):
    response = request_code(client)
    assert response.status_code == 200
    assert response.get_json()["expiresInSeconds"] == 300
    assert response.get_json()["resendAfterSeconds"] == 60
    assert outbox[0]["to"] == EMAIL

    otp = last_otp(outbox)
    verified = verify(client, otp)
    assert verified.status_code == 200
    token = verified.get_json()["resetToken"]

    assert reset(client, token).status_code == 200
    assert login(client, OLD_PASSWORD).status_code == 401
    assert login(client, NEW_PASSWORD).status_code == 200

    # The reset token cannot be reused.
    assert reset(client, token, "AnotherPass789").status_code == 400


def test_unknown_email_gets_identical_response_and_no_email(client, outbox):
    known = request_code(client)
    unknown = request_code(client, "nobody@example.com")
    assert unknown.status_code == known.status_code == 200
    assert unknown.get_json() == known.get_json()
    assert len(outbox) == 1


def test_staff_accounts_are_not_reset_through_mobile_recovery(client, outbox):
    response = request_code(client, "elena.cruz@university.edu.ph")
    assert response.status_code == 200
    assert outbox == []


def test_resend_cooldown_blocks_second_email(client, outbox):
    request_code(client)
    again = request_code(client)
    assert again.status_code == 200
    assert len(outbox) == 1

    shift_user(reset_otp_sent_at=61)
    request_code(client)
    assert len(outbox) == 2


def test_new_otp_replaces_old_one(client, outbox):
    request_code(client)
    first = last_otp(outbox)
    shift_user(reset_otp_sent_at=61)
    request_code(client)
    second = last_otp(outbox)
    if first != second:
        assert verify(client, first).status_code == 400
    assert verify(client, second).status_code == 200


def test_otp_cannot_be_reused(client, outbox):
    request_code(client)
    otp = last_otp(outbox)
    assert verify(client, otp).status_code == 200
    assert verify(client, otp).status_code == 400


def test_otp_expires_after_five_minutes(client, outbox):
    request_code(client)
    otp = last_otp(outbox)
    shift_user(reset_otp_expires_at=301)
    response = verify(client, otp)
    assert response.status_code == 400
    assert response.get_json()["error"] == password_reset.INVALID_CODE_MESSAGE


def test_incorrect_attempts_are_limited(client, outbox):
    request_code(client)
    otp = last_otp(outbox)
    wrong = "000000" if otp != "000000" else "111111"
    for _ in range(5):
        assert verify(client, wrong).status_code == 400
    # Even the correct code is rejected after the limit; a new code is required.
    assert verify(client, otp).status_code == 400

    shift_user(reset_otp_sent_at=61)
    request_code(client)
    assert verify(client, last_otp(outbox)).status_code == 200


def test_wrong_code_message_is_same_for_unknown_email(client, outbox):
    request_code(client)
    known = verify(client, "000000" if last_otp(outbox) != "000000" else "111111")
    unknown = verify(client, "123456", email="nobody@example.com")
    assert known.status_code == unknown.status_code == 400
    assert known.get_json() == unknown.get_json()


def test_reset_requires_verified_token_and_strong_password(client, outbox):
    assert reset(client, "forged-token").status_code == 400

    request_code(client)
    token = verify(client, last_otp(outbox)).get_json()["resetToken"]
    assert reset(client, token, "short").status_code == 400
    assert reset(client, token).status_code == 200


def test_reset_token_expires(client, outbox):
    request_code(client)
    token = verify(client, last_otp(outbox)).get_json()["resetToken"]
    shift_user(reset_token_expires_at=601)
    assert reset(client, token).status_code == 400
    assert login(client, OLD_PASSWORD).status_code == 200


def test_delivery_failure_returns_error_and_stores_no_code(client, monkeypatch):
    monkeypatch.setitem(app.config, "SMTP_HOST", "smtp.test")
    monkeypatch.setitem(app.config, "SMTP_FROM", "noreply@test")

    def boom(*args, **kwargs):
        raise password_reset.EmailDeliveryError("connection refused")

    monkeypatch.setattr(password_reset, "send_email", boom)
    response = request_code(client)
    assert response.status_code == 503
    with app.app_context():
        assert User.query.filter_by(email=EMAIL).first().reset_otp_hash is None


def _run_fake_smtp_server():
    """Minimal SMTP sink so the real smtplib delivery path is exercised."""
    import socket
    import threading

    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    received: dict = {"data": ""}

    def serve():
        conn, _ = server.accept()
        with conn, conn.makefile("rwb") as stream:
            def send(line):
                stream.write((line + "\r\n").encode())
                stream.flush()

            send("220 test ESMTP")
            in_data = False
            while True:
                raw = stream.readline()
                if not raw:
                    break
                line = raw.decode(errors="replace").rstrip("\r\n")
                if in_data:
                    if line == ".":
                        in_data = False
                        send("250 queued")
                    else:
                        received["data"] += line + "\n"
                    continue
                command = line.upper()
                if command.startswith("EHLO") or command.startswith("HELO"):
                    send("250 test")
                elif command.startswith("DATA"):
                    in_data = True
                    send("354 go ahead")
                elif command.startswith("QUIT"):
                    send("221 bye")
                    break
                else:
                    send("250 ok")
        server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return server.getsockname()[1], received, thread


def test_real_smtp_delivery_path_sends_the_code(client, monkeypatch):
    port, received, thread = _run_fake_smtp_server()
    monkeypatch.setitem(app.config, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setitem(app.config, "SMTP_PORT", port)
    monkeypatch.setitem(app.config, "SMTP_SECURITY", "none")
    monkeypatch.setitem(app.config, "SMTP_USERNAME", "")
    monkeypatch.setitem(app.config, "SMTP_FROM", "FacultyLink <noreply@test>")

    assert request_code(client).status_code == 200
    thread.join(timeout=5)

    message = received["data"]
    assert f"To: {EMAIL}" in message
    assert "Subject: Your FacultyLink password reset code" in message
    code = re.search(r"code is: (\d{6})", message).group(1)
    assert verify(client, code).status_code == 200


def test_unreachable_smtp_server_is_reported(client, monkeypatch):
    monkeypatch.setitem(app.config, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setitem(app.config, "SMTP_PORT", 1)  # nothing listens here
    monkeypatch.setitem(app.config, "SMTP_SECURITY", "none")
    monkeypatch.setitem(app.config, "SMTP_FROM", "noreply@test")
    response = request_code(client)
    assert response.status_code == 503
    assert "could not send" in response.get_json()["error"].lower()


def test_invalid_email_is_rejected(client, outbox):
    assert request_code(client, "not-an-email").status_code == 400
