"""Database plumbing shared by all modules.

Each module owns its own tables (and table-name prefix) but they share one engine and one
transaction per request. Sharing the *transaction* is a pragmatic modular-monolith choice:
an appointment and its audit entry commit atomically. See ADR-0001.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import DateTime, Engine, MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from careslot.shared.config import get_settings

# Deterministic constraint names make Alembic autogenerate diffs stable and reviewable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores timezone-aware datetimes and always returns them in UTC.

    Rejects naive datetimes at the boundary - a naive appointment time is a bug waiting for
    the next daylight-saving change.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("naive datetime not allowed")
        return value

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        return value.astimezone(UTC) if value is not None else None


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(url), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session (and transaction) per request."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
