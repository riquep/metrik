"""Fixtures do banco de teste (Postgres real — RLS não existe em SQLite).

Requer um Postgres com os roles `metrik_admin` (superuser, dono das
tabelas — usado só pra setup/teardown dos testes) e `metrik_app` (role
restrito, sujeito a RLS — o que a aplicação de verdade usaria) já
existentes, e um banco `metrik_test` que o `metrik_admin` possa migrar.
Ver `backend/README.md` para os comandos de setup.

Se o Postgres de teste não estiver acessível, os testes que dependem dele
são pulados (skip) em vez de falhar — os testes do parser/harness
continuam rodando normalmente sem banco nenhum.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).parent.parent

TEST_ADMIN_DATABASE_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL",
    "postgresql+psycopg://metrik_admin:metrik_admin_dev_pw@localhost:5432/metrik_test",
)
TEST_APP_DATABASE_URL = os.environ.get(
    "TEST_APP_DATABASE_URL",
    "postgresql+psycopg://metrik_app:metrik_app_dev_pw@localhost:5432/metrik_test",
)

_TENANT_TABLES = "clinic_staff, patients, evaluations, metrics, invites, clinics"


def _run_alembic(command: str, target: str) -> None:
    subprocess.run(
        ["alembic", command, target],
        cwd=BACKEND_DIR,
        env={**os.environ, "ADMIN_DATABASE_URL": TEST_ADMIN_DATABASE_URL},
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def db_available() -> None:
    try:
        engine = create_engine(TEST_ADMIN_DATABASE_URL)
        with engine.connect():
            pass
        engine.dispose()
    except Exception as exc:  # pragma: no cover - ambiente sem Postgres
        pytest.skip(f"Postgres de teste indisponível em {TEST_ADMIN_DATABASE_URL}: {exc}")


@pytest.fixture(scope="session")
def migrated_db(db_available: None):
    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")
    yield


@pytest.fixture
def admin_session_factory(migrated_db: None):
    engine = create_engine(TEST_ADMIN_DATABASE_URL)
    factory = sessionmaker(bind=engine)
    yield factory
    with engine.connect() as conn:
        conn.execute(text(f"TRUNCATE {_TENANT_TABLES} RESTART IDENTITY CASCADE"))
        conn.commit()
    engine.dispose()


@pytest.fixture
def app_session_factory(admin_session_factory):
    engine = create_engine(TEST_APP_DATABASE_URL)
    yield sessionmaker(bind=engine)
    engine.dispose()
