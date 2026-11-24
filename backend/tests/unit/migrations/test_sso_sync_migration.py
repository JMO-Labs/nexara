"""
@file tests/unit/migrations/test_sso_sync_migration.py
@brief 0071_sso_sync folds *_claim columns into claim_mapping and restores them.
"""

import os
import subprocess
import sys
from pathlib import Path

import psycopg2
import pytest

BACKEND = Path(__file__).resolve().parents[3]
DB = "nexara_mig_sso"
CID = "00000000-0000-0000-0000-000000000001"
ADMIN = dict(host="localhost", user="nexara", password="nexara", dbname="postgres")


def _alembic(*args: str) -> None:
    env = {
        **os.environ,
        "DATABASE_URL": f"postgresql+asyncpg://nexara:nexara@localhost:5432/{DB}",
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def scratch_db():
    try:
        conn = psycopg2.connect(**ADMIN)
    except psycopg2.OperationalError:
        pytest.skip("postgres unavailable")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS {DB}")
    cur.execute(f"CREATE DATABASE {DB}")
    yield
    cur.execute(f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)")
    conn.close()


def test_claim_columns_fold_into_claim_mapping(scratch_db) -> None:
    """@brief email_claim=mail lands in claim_mapping.email; downgrade restores it."""
    _alembic("upgrade", "0070_twofactor")
    conn = psycopg2.connect(**{**ADMIN, "dbname": DB})
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("INSERT INTO communities (id) VALUES (%s) ON CONFLICT DO NOTHING", (CID,))
    cols = "community_id, slug, display_name, client_id, client_secret_encrypted"
    sql = f"INSERT INTO oauth_providers ({cols}, email_claim, name_claim, claim_mapping) "
    cur.execute(sql + "VALUES (%s,'a','A','c','s','mail','full_name',%s)", (CID, '{"name":"nick"}'))
    cur.execute(sql + "VALUES (%s,'b','B','c','s','email','name','{}')", (CID,))
    _alembic("upgrade", "0071_sso_sync")
    cur.execute(
        "SELECT slug, claim_mapping, allowed_domains, username_claim, sync_profile "
        "FROM oauth_providers ORDER BY slug"
    )
    a, b = cur.fetchall()
    assert a[1] == {"email": "mail", "name": "nick"}
    assert a[2:] == ([], "preferred_username", True)
    assert b[1] == {}
    _alembic("downgrade", "0070_twofactor")
    cur.execute("SELECT email_claim, name_claim FROM oauth_providers ORDER BY slug")
    assert cur.fetchall() == [("mail", "nick"), ("email", "name")]
    conn.close()
