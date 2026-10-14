"""Consent decisions: append-only history per patient and purpose (ADR-0007).

Revision ID: eaa70c571ae8
Revises: ed9f2c4c9a5c
Create Date: 2026-10-14 14:31:19.290739
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "eaa70c571ae8"
down_revision: str | None = "ed9f2c4c9a5c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "con_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_con_decisions")),
    )
    op.create_index(
        "ix_con_decisions_patient_time", "con_decisions", ["patient_id", "decided_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_con_decisions_patient_time", table_name="con_decisions")
    op.drop_table("con_decisions")
