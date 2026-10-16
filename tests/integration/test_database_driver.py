"""Check database driver loading without connecting to a real database."""

import os
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

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
            dedent(f"""
                from sqlalchemy import event
                from app.db.session import engine

                assert engine.dialect.name == {dialect!r}

                class ConnectionIntercepted(Exception):
                    pass

                @event.listens_for(engine, 'do_connect')
                def check_connection_options(dialect, connection_record, args, params):
                    if dialect.driver == 'psycopg':
                        assert 'prepare_threshold' in params
                        assert params['prepare_threshold'] is None
                    else:
                        assert 'prepare_threshold' not in params
                    if dialect.name == 'sqlite':
                        assert params['check_same_thread'] is False
                    # Stop before opening any real database connection.
                    raise ConnectionIntercepted()

                try:
                    engine.connect()
                except ConnectionIntercepted:
                    pass
                else:
                    raise AssertionError('Connection was not intercepted')
                finally:
                    engine.dispose()
            """),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
