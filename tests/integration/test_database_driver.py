"""Check database driver loading without connecting to a real database."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "url,dialect",
    [
        ("postgres://test:test@localhost/test", "postgresql"),
        ("postgresql://test:test@localhost/test", "postgresql"),
        ("postgresql+psycopg://test:test@localhost/test", "postgresql"),
        ("postgresql+psycopg2://test:test@localhost/test", "postgresql"),
        ("sqlite:///:memory:", "sqlite"),
    ],
)
def test_database_module_loads_driver_without_connecting(url, dialect):
    env = os.environ.copy()
    env.update(DATABASE_URL=url, SECRET_KEY="test-only-secret", CORS_ORIGINS="[]")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.db.session import engine; "
            f"assert engine.dialect.name == {dialect!r}; "
            "engine.dispose()",
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
