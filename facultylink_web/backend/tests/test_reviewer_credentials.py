"""Reviewer temporary passwords and credential email delivery."""

import json
import socket
import sys
import threading
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import reviewer_credentials
from password_reset import EmailDeliveryError, EmailNotConfigured, password_problem


def test_blank_password_is_generated_and_meets_the_shared_rules():
    chosen, error = reviewer_credentials.choose_password("   ", lambda: "generated-pass")
    assert error is None
    assert chosen == "generated-pass"
    assert password_problem(chosen) is None

    chosen, error = reviewer_credentials.choose_password("", lambda: "tiny")
    assert chosen is None
    assert error == "A temporary password could not be generated."


def test_manual_password_uses_the_shared_rules():
    chosen, error = reviewer_credentials.choose_password("short", lambda: "unused-password")
    assert chosen is None
    assert error == "Use at least 8 characters."

    chosen, error = reviewer_credentials.choose_password("Reviewer-Pass-1", lambda: "unused-password")
    assert error is None
    assert chosen == "Reviewer-Pass-1"


def test_credential_message_includes_account_login_and_first_change():
    body = reviewer_credentials.reviewer_credential_message(
        "Avery Santos",
        "avery@example.edu",
        "temporary-secret",
        "http://127.0.0.1:5000/login.html",
    )
    assert "FacultyLink account" in body
    assert "Login email: avery@example.edu" in body
    assert "Temporary password: temporary-secret" in body
    assert "FacultyLink Web Portal" in body
    assert "http://127.0.0.1:5000/login.html" in body
    assert "first login" in body
    assert "change this temporary password" in body


def _fake_smtp():
    received = {"data": ""}
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    def serve():
        connection, _address = server.accept()
        with connection:
            in_data = False
            file = connection.makefile("rwb")

            def send(line):
                file.write((line + "\r\n").encode())
                file.flush()

            send("220 test")
            while True:
                raw = file.readline()
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


def test_smtp_delivery_sends_the_credential_message():
    port, received, thread = _fake_smtp()
    reviewer_credentials.deliver_reviewer_credentials(
        {
            "SMTP_HOST": "127.0.0.1",
            "SMTP_PORT": port,
            "SMTP_SECURITY": "none",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
            "SMTP_FROM": "FacultyLink <noreply@example.edu>",
        },
        "Avery Santos",
        "avery@example.edu",
        "temporary-secret",
        "http://127.0.0.1:5000/login.html",
    )
    thread.join(timeout=5)
    message = received["data"]
    assert "To: avery@example.edu" in message
    assert "Subject: Your FacultyLink reviewer account" in message
    assert "Login email: avery@example.edu" in message
    assert "Temporary password: temporary-secret" in message
    assert "FacultyLink Web Portal" in message
    assert "first login" in message


def test_missing_smtp_settings_are_reported_without_claiming_delivery():
    with pytest.raises(EmailNotConfigured) as caught:
        reviewer_credentials.deliver_reviewer_credentials(
            {"SMTP_HOST": "", "SMTP_FROM": "", "SMTP_PORT": 587},
            "Avery Santos",
            "avery@example.edu",
            "temporary-secret",
            "http://127.0.0.1:5000/login.html",
        )
    message = reviewer_credentials.email_failure_message(caught.value, account_created=True)
    assert "not configured" in message
    assert "SMTP_HOST" in message
    assert "temporary-secret" not in message
    assert "was not kept" in message


def test_unreachable_smtp_is_reported_without_changing_an_existing_password():
    with pytest.raises(EmailDeliveryError):
        reviewer_credentials.deliver_reviewer_credentials(
            {
                "SMTP_HOST": "127.0.0.1",
                "SMTP_PORT": 1,
                "SMTP_SECURITY": "none",
                "SMTP_FROM": "noreply@example.edu",
            },
            "Avery Santos",
            "avery@example.edu",
            "temporary-secret",
            "http://127.0.0.1:5000/login.html",
        )
    message = reviewer_credentials.email_failure_message(
        EmailDeliveryError("connection refused"),
        account_created=False,
    )
    assert "could not be delivered" in message
    assert "was not changed" in message
    assert "temporary-secret" not in message


def _load_web():
    import importlib.util

    spec = importlib.util.spec_from_file_location("facultylink_web_app", BACKEND / "app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["facultylink_web_app"] = module
    spec.loader.exec_module(module)
    return module


def _cleanup(webapp, email):
    conn = webapp.connect()
    row = conn.execute("SELECT id FROM users WHERE lower(email) = %s", (email,)).fetchone()
    if row:
        webapp.delete_user_rows(conn, row["id"])
    conn.execute("DELETE FROM audit_logs WHERE detail ILIKE %s", (f"%{email}%",))
    conn.commit()
    conn.close()


def test_reviewer_account_email_login_and_access(monkeypatch):
    webapp = _load_web()
    conn = webapp.connect()
    admin = conn.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not admin:
        pytest.skip("No administrator account is available.")

    email = f"reviewer-cred-{uuid.uuid4().hex[:10]}@example.edu"
    captured = {}

    def capture(_config, name, address, password, portal):
        captured["name"] = name
        captured["email"] = address
        captured["password"] = password
        captured["portal"] = portal

    monkeypatch.setattr(webapp.reviewer_credentials, "deliver_reviewer_credentials", capture)
    client = webapp.app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["user_id"] = admin["id"]
            sess["role"] = "admin"

        rejected = client.post(
            "/api/reviewers",
            json={"fullName": "Test Reviewer", "email": email, "password": "short"},
        )
        assert rejected.status_code == 400
        assert "8 characters" in rejected.get_json()["error"]

        created = client.post(
            "/api/reviewers",
            json={
                "fullName": "Test Reviewer",
                "email": email,
                "department": "Institutional Review",
                "password": "",
            },
        )
        body = created.get_json()
        assert created.status_code == 201
        assert body["emailSent"] is True
        assert "temporaryPassword" not in body
        assert captured["password"] not in json.dumps(body)
        assert body["reviewer"]["role"] == "reviewer"
        assert body["reviewer"]["email"] == email
        assert password_problem(captured["password"]) is None
        assert "login.html" in captured["portal"]

        duplicate = client.post(
            "/api/reviewers",
            json={"fullName": "Test Reviewer", "email": email, "password": "Another-Pass-1"},
        )
        assert duplicate.status_code == 409

        conn = webapp.connect()
        stored = conn.execute("SELECT * FROM users WHERE lower(email) = %s", (email,)).fetchone()
        audit = conn.execute(
            "SELECT detail FROM audit_logs WHERE detail ILIKE %s ORDER BY id DESC LIMIT 1",
            (f"%{email}%",),
        ).fetchone()
        conn.close()
        assert stored["role"] == "reviewer"
        assert stored["must_change_password"] is True
        assert stored["password_hash"] != captured["password"]
        assert webapp.check_password_hash(stored["password_hash"], captured["password"])
        assert captured["password"] not in audit["detail"]

        reviewer = webapp.app.test_client()
        signed_in = reviewer.post("/api/login", json={"identity": email, "password": captured["password"]})
        session_body = signed_in.get_json()
        assert signed_in.status_code == 200
        assert session_body["role"] == "reviewer"
        assert session_body["mustChangePassword"] is True
        blocked = reviewer.get("/api/state")
        assert blocked.status_code == 403
        assert blocked.get_json()["mustChangePassword"] is True

        weak = reviewer.post(
            "/api/account/password",
            json={"currentPassword": captured["password"], "newPassword": "short"},
        )
        assert weak.status_code == 400
        changed = reviewer.post(
            "/api/account/password",
            json={"currentPassword": captured["password"], "newPassword": "Replacement-Pass-1"},
        )
        assert changed.status_code == 200
        assert changed.get_json()["mustChangePassword"] is False
        state = reviewer.get("/api/state")
        assert state.status_code == 200
        state_body = state.get_json()
        assert state_body["faculty"] == []
        assert state_body["documents"] == []
        assert reviewer.put("/api/kra-settings", json={"indicators": {}}).status_code == 403

        old_login = webapp.app.test_client()
        assert old_login.post(
            "/api/login", json={"identity": email, "password": captured["password"]}
        ).status_code == 401

        conn = webapp.connect()
        previous_hash = conn.execute(
            "SELECT password_hash FROM users WHERE id = %s", (stored["id"],)
        ).fetchone()["password_hash"]
        conn.close()

        def refuse(*_args, **_kwargs):
            raise EmailDeliveryError("connection refused")

        monkeypatch.setattr(webapp.reviewer_credentials, "deliver_reviewer_credentials", refuse)
        failed = client.post(f"/api/reviewers/{stored['id']}/credentials")
        assert failed.status_code == 502
        assert "not changed" in failed.get_json()["error"]
        conn = webapp.connect()
        unchanged = conn.execute("SELECT password_hash FROM users WHERE id = %s", (stored["id"],)).fetchone()
        conn.close()
        assert unchanged["password_hash"] == previous_hash

        monkeypatch.setattr(webapp.reviewer_credentials, "deliver_reviewer_credentials", capture)
        reissued = client.post(f"/api/reviewers/{stored['id']}/credentials")
        assert reissued.status_code == 200
        assert reissued.get_json()["emailSent"] is True
        assert captured["password"] not in json.dumps(reissued.get_json())
        conn = webapp.connect()
        updated = conn.execute(
            "SELECT password_hash, must_change_password FROM users WHERE id = %s",
            (stored["id"],),
        ).fetchone()
        resent_audit = conn.execute(
            "SELECT detail FROM audit_logs WHERE action = 'Reissued reviewer credentials' AND detail ILIKE %s",
            (f"%{email}%",),
        ).fetchone()
        conn.close()
        assert updated["must_change_password"] is True
        assert webapp.check_password_hash(updated["password_hash"], captured["password"])
        assert captured["password"] not in resent_audit["detail"]
        assert updated["password_hash"] != previous_hash
    finally:
        _cleanup(webapp, email)


def test_manual_password_is_emailed_but_not_returned(monkeypatch):
    webapp = _load_web()
    conn = webapp.connect()
    admin = conn.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not admin:
        pytest.skip("No administrator account is available.")

    email = f"reviewer-manual-{uuid.uuid4().hex[:10]}@example.edu"
    supplied = "Manual-Reviewer-1"
    captured = {}

    def capture(_config, _name, _address, password, _portal):
        captured["password"] = password

    monkeypatch.setattr(webapp.reviewer_credentials, "deliver_reviewer_credentials", capture)
    client = webapp.app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["user_id"] = admin["id"]
        created = client.post(
            "/api/reviewers",
            json={"fullName": "Manual Reviewer", "email": email, "password": supplied},
        )
        body = created.get_json()
        assert created.status_code == 201
        assert body["emailSent"] is True
        assert captured["password"] == supplied
        assert supplied not in json.dumps(body)
        conn = webapp.connect()
        stored = conn.execute("SELECT password_hash FROM users WHERE lower(email) = %s", (email,)).fetchone()
        conn.close()
        assert webapp.check_password_hash(stored["password_hash"], supplied)
    finally:
        _cleanup(webapp, email)


def test_faculty_account_email_and_must_change(monkeypatch):
    webapp = _load_web()
    conn = webapp.connect()
    admin = conn.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not admin:
        pytest.skip("No administrator account is available.")

    email = f"faculty-cred-{uuid.uuid4().hex[:10]}@example.edu"
    captured = {}

    def capture(_config, name, address, password):
        captured["name"] = name
        captured["email"] = address
        captured["password"] = password

    monkeypatch.setattr(webapp.reviewer_credentials, "deliver_faculty_credentials", capture)
    client = webapp.app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["user_id"] = admin["id"]
        created = client.post(
            "/api/faculty",
            json={
                "fullName": "Test Faculty",
                "email": email,
                "department": "Education",
                "password": "",
            },
        )
        body = created.get_json()
        assert created.status_code == 201
        assert body["emailSent"] is True
        assert "temporaryPassword" not in body
        assert "mobile app" not in json.dumps(body)
        conn = webapp.connect()
        stored = conn.execute("SELECT must_change_password FROM users WHERE lower(email) = %s", (email,)).fetchone()
        conn.close()
        assert stored["must_change_password"] is True
        assert captured["email"] == email
    finally:
        _cleanup(webapp, email)


def test_email_failure_keeps_the_account_and_hides_the_password(monkeypatch):
    webapp = _load_web()
    conn = webapp.connect()
    admin = conn.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    conn.close()
    if not admin:
        pytest.skip("No administrator account is available.")

    email = f"reviewer-fail-{uuid.uuid4().hex[:10]}@example.edu"

    def refuse(*_args, **_kwargs):
        raise EmailNotConfigured(["SMTP_HOST", "SMTP_FROM"])

    monkeypatch.setattr(webapp.reviewer_credentials, "deliver_reviewer_credentials", refuse)
    client = webapp.app.test_client()
    try:
        with client.session_transaction() as sess:
            sess["user_id"] = admin["id"]
        created = client.post(
            "/api/reviewers",
            json={"fullName": "Failed Mail Reviewer", "email": email, "password": ""},
        )
        body = created.get_json()
        text = json.dumps(body)
        assert created.status_code == 201
        assert body["emailSent"] is False
        assert "SMTP_HOST" in body["emailError"]
        assert "temporaryPassword" not in body
        assert "FL-" not in text
        conn = webapp.connect()
        stored = conn.execute(
            "SELECT role, password_hash, must_change_password FROM users WHERE lower(email) = %s",
            (email,),
        ).fetchone()
        audit = conn.execute(
            "SELECT detail FROM audit_logs WHERE detail ILIKE %s ORDER BY id DESC LIMIT 1",
            (f"%{email}%",),
        ).fetchone()
        conn.close()
        assert stored["role"] == "reviewer"
        assert stored["must_change_password"] is True
        assert stored["password_hash"]
        assert "FL-" not in audit["detail"]
        assert "not delivered" in audit["detail"]
    finally:
        _cleanup(webapp, email)
