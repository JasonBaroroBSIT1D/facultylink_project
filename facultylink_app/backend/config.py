import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _require_postgres_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required. Set it in backend/.env to a PostgreSQL URL, e.g. "
            "postgresql+psycopg://postgres:YOUR_PASSWORD@127.0.0.1:5432/facultylink"
        )
    normalized = url.lower()
    if normalized.startswith("sqlite:"):
        raise RuntimeError(
            "SQLite is disabled for FacultyLink. Use a PostgreSQL DATABASE_URL "
            "(postgresql+psycopg://...)."
        )
    if not (
        normalized.startswith("postgresql:")
        or normalized.startswith("postgresql+")
        or normalized.startswith("postgres:")
        or normalized.startswith("postgres+")
    ):
        raise RuntimeError(
            "DATABASE_URL must be a PostgreSQL connection string "
            "(postgresql+psycopg://user:pass@host:5432/facultylink)."
        )
    return url


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "facultylink-dev-secret")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "facultylink-jwt-dev-secret-key-32b")
    SQLALCHEMY_DATABASE_URI = _require_postgres_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
