"""DATABASE_URL resolution.

db.py resolves the URL at import time, and conftest has already set it for the
test session, so these run in a subprocess to exercise the real startup path
with a controlled environment.
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SQLITE = "sqlite:///./dealsieve.db"


def resolved_url(value: str | None) -> str:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    if value is not None:
        env["DATABASE_URL"] = value
    result = subprocess.run(
        [sys.executable, "-c", "from app.db import DATABASE_URL; print(DATABASE_URL)"],
        cwd=BACKEND, env=env, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def test_empty_database_url_falls_back_to_sqlite():
    """Render passes an unset blueprint variable as "", which must not crash."""
    assert resolved_url("") == SQLITE


def test_unset_database_url_falls_back_to_sqlite():
    assert resolved_url(None) == SQLITE


def test_postgres_urls_get_an_explicit_driver():
    assert resolved_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert resolved_url("postgresql://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
