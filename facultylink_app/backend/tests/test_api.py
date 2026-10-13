import io

from app import app
from models import User


def faculty_headers(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "maria.santos@university.edu.ph", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.get_json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def staff_headers(client, email="elena.cruz@university.edu.ph", password="reviewer123"):
    response = client.post("/api/auth/staff-login", json={"email": email, "password": password})
    assert response.status_code == 200
    token = response.get_json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def test_root_status(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_faculty_login_and_profile(client):
    headers = faculty_headers(client)
    me = client.get("/api/me", headers=headers)
    assert me.status_code == 200
    assert me.get_json()["fullName"] == "Maria Santos"


def test_faculty_read_apis(client):
    headers = faculty_headers(client)
    documents = client.get("/api/documents", headers=headers)
    scores = client.get("/api/assessment/kra-scores", headers=headers)
    requirements = client.get("/api/assessment/requirements", headers=headers)
    simulation = client.get("/api/simulation", headers=headers)
    notifications = client.get("/api/notifications", headers=headers)
    period = client.get("/api/preparation-period")
    assert documents.status_code == 200
    assert len(documents.get_json()) == 11
    assert scores.status_code == 200
    assert {row["type"] for row in scores.get_json()} == {
        "instruction",
        "research",
        "extension",
        "professionalDevelopment",
    }
    assert requirements.status_code == 200
    assert simulation.status_code == 200
    assert simulation.get_json()["currentRank"] == "Instructor I"
    assert notifications.status_code == 200
    assert period.status_code == 200
    cycle_name = period.get_json()["cycleName"]
    assert "AY 2025" in cycle_name or cycle_name == "Rank Upgrade and Reclassification"
    assert period.get_json()["startDate"]
    assert period.get_json()["endDate"]


def test_register_request(client):
    response = client.post(
        "/api/auth/register",
        json={"fullName": "Jose Reyes", "email": "jose.reyes@university.edu.ph"},
    )
    assert response.status_code == 201


def test_document_upload_and_duplicate(client):
    headers = faculty_headers(client)
    payload = {
        "title": "Journal Article on Inquiry Classrooms",
        "category": "researchPublications",
        "kra": "research",
        "author": "Maria Santos",
    }
    files = {"file": (io.BytesIO(b"same-bytes-for-hash"), "article.txt")}
    created = client.post("/api/documents", data={**payload, **files}, headers=headers)
    assert created.status_code == 201
    body = created.get_json()
    assert body["kra"] == "research"
    assert body["status"] == "pendingReview"

    duplicate = client.post(
        "/api/documents",
        data={**payload, "file": (io.BytesIO(b"same-bytes-for-hash"), "article-copy.txt")},
        headers=headers,
    )
    assert duplicate.status_code == 409


def test_reviewer_queue_and_validate(client):
    headers = staff_headers(client)
    queue = client.get("/api/review/queue", headers=headers)
    assert queue.status_code == 200
    assert any(item["id"] == "doc-003" for item in queue.get_json())

    reviewed = client.post(
        "/api/documents/doc-003/review",
        json={"action": "validate", "points": 5, "feedback": "Observation accepted."},
        headers=headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.get_json()["status"] == "validated"


def test_admin_can_read_users_and_rules(client):
    headers = staff_headers(client, "admin@university.edu.ph", "admin123")
    users = client.get("/api/admin/users", headers=headers)
    rules = client.get("/api/admin/scoring-rules", headers=headers)
    assert users.status_code == 200
    emails = {item["email"] for item in users.get_json()}
    assert "maria.santos@university.edu.ph" in emails
    assert rules.status_code == 200
    assert any(rule["kra"] == "research" for rule in rules.get_json())


def test_faculty_cannot_open_review_queue(client):
    headers = faculty_headers(client)
    response = client.get("/api/review/queue", headers=headers)
    assert response.status_code == 403


def test_seeded_demo_accounts_exist(client):
    with app.app_context():
        assert User.query.filter_by(email="maria.santos@university.edu.ph").first()
        assert User.query.filter_by(email="elena.cruz@university.edu.ph").first()
        assert User.query.filter_by(email="admin@university.edu.ph").first()
