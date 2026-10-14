"""Alembic environment.

The database URL comes from application settings (environment), never from alembic.ini, so
no credentials live in the repository.
"""

from typing import Any, Literal

from alembic import context
from sqlalchemy import engine_from_config, pool

from careslot.shared.config import get_settings
from careslot.shared.db import Base, UTCDateTime
from careslot.shared.models import import_all_models

import_all_models()
target_metadata = Base.metadata
config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | Literal[False]:
    # Migrations must not import application types: they are frozen history, the app evolves.
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
