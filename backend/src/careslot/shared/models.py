"""Registry of ORM model modules, so Alembic and tests see the full schema.

Each bounded context registers its infrastructure `models` module here. This file is part of
the composition root's knowledge, not of any module.
"""

import importlib

MODEL_MODULES: tuple[str, ...] = (
    "careslot.modules.scheduling.infrastructure.models",
    "careslot.modules.patients.infrastructure.models",
    "careslot.modules.audit.infrastructure.models",
)


def import_all_models() -> None:
    for name in MODEL_MODULES:
        importlib.import_module(name)
