import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")


def _postgres_test_url() -> str:
    explicit = (os.getenv("TEST_DATABASE_URL") or "").strip()
    if explicit:
        if explicit.lower().startswith("sqlite:"):
            raise RuntimeError("SQLite is disabled. Use a PostgreSQL TEST_DATABASE_URL.")
        return explicit

    base = (os.getenv("DATABASE_URL") or "").strip()
    if not base:
        raise RuntimeError(
            "Set DATABASE_URL or TEST_DATABASE_URL to a PostgreSQL URL for tests."
        )
    if base.lower().startswith("sqlite:"):
        raise RuntimeError("SQLite is disabled. Use a PostgreSQL DATABASE_URL.")

    scheme, rest = base.split("://", 1)
    parsed = urlparse(f"http://{rest}")
    rebuilt = urlunparse(("", parsed.netloc, "/facultylink_test", "", "", ""))
    return f"{scheme}://{rebuilt.lstrip('/')}"


def _psycopg_dsn(sqlalchemy_url: str, dbname: str | None = None) -> str:
    scheme, rest = sqlalchemy_url.split("://", 1)
    driver = scheme.split("+", 1)[0]
    if driver == "postgres":
        driver = "postgresql"
    parsed = urlparse(f"{driver}://{rest}")
    path = f"/{dbname}" if dbname else (parsed.path or "/postgres")
    return urlunparse((driver, parsed.netloc, path, "", "", ""))


def _ensure_database_exists(sqlalchemy_url: str) -> None:
    parsed = urlparse(
        "http://" + sqlalchemy_url.split("://", 1)[1]
    )
    db_name = (parsed.path or "").lstrip("/") or "facultylink_test"
    admin_dsn = _psycopg_dsn(sqlalchemy_url, "postgres")
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{db_name}"')


# Force the whole pytest session onto an isolated Postgres database so
# drop_all/seed never wipe the live facultylink data.
_TEST_DATABASE_URL = _postgres_test_url()
_ensure_database_exists(_TEST_DATABASE_URL)
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
os.environ["SEED_DEMO_DATA"] = "0"


@pytest.fixture()
def client():
    from app import app, db
    from seed import seed_if_empty

    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = _TEST_DATABASE_URL
    app.config["SEED_DEMO_DATA"] = False

    with app.app_context():
        db.session.remove()
        db.engine.dispose()
        db.drop_all()
        db.create_all()
        seed_if_empty()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
