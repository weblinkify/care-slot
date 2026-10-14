"""Optional, closed-list cancellation reason on appointments.

Zero-downtime safe ("expand" step only): a nullable column with no default is a metadata-only
change in PostgreSQL, so it takes no long table lock and old app versions keep working.

Note: Alembic autogenerate does NOT detect CHECK constraints; the constraint below was added by
hand. Always read generated migrations before committing them.

Revision ID: f641fd5a0781
Revises: eaa70c571ae8
Create Date: 2026-10-14 15:22:51.666613
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f641fd5a0781"
down_revision: str | None = "eaa70c571ae8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sched_appointments", sa.Column("cancellation_reason", sa.String(length=32), nullable=True)
    )
    op.create_check_constraint(
        "valid_cancellation_reason",  # naming convention prefixes it: ck_sched_appointments_...
        "sched_appointments",
        "cancellation_reason IN "
        "('scheduling-conflict', 'feeling-better', 'booked-elsewhere', 'other')",
    )


def downgrade() -> None:
    op.drop_constraint("valid_cancellation_reason", "sched_appointments", type_="check")
    op.drop_column("sched_appointments", "cancellation_reason")
