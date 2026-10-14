"""Integration test fixtures: a throwaway PostgreSQL container per test session.

The schema is created by running the real Alembic migrations (not `create_all`), so every
integration run also proves the migrations work and match the models.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from careslot.shared import config as config_module
from careslot.shared import db as db_module
from careslot.shared.principal import Role
from careslot.shared.security import issue_token

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        url = pg.get_connection_url()
        os.environ["CARESLOT_DATABASE_URL"] = url
        os.environ["CARESLOT_ENVIRONMENT"] = "test"
        config_module.get_settings.cache_clear()
        db_module.get_engine.cache_clear()
        db_module.get_session_factory.cache_clear()

        cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "migrations"))
        command.upgrade(cfg, "head")
        yield url


@pytest.fixture(autouse=True)
def _clean_tables(database_url: str) -> Iterator[None]:
    yield
    with db_module.get_engine().begin() as conn:
        tables = conn.scalars(
            text(
                "SELECT tablename FROM pg_tables"
                " WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).all()
        if tables:
            # Table names come from the catalogue, not user input.
            conn.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))


@pytest.fixture
def session(database_url: str) -> Iterator[Session]:
    with db_module.get_session_factory()() as s:
        yield s


@pytest.fixture
def client(database_url: str) -> TestClient:
    from careslot.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def bearer(subject: UUID, role: Role) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_token(subject, role)}"}


def future(hours: float) -> datetime:
    start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    return start + timedelta(hours=hours)


def new_id() -> UUID:
    return uuid4()
