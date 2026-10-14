"""Patients (encrypted identity code) and the append-only, hash-chained audit log.

The audit table gets a trigger that rejects UPDATE, DELETE and TRUNCATE for *every* database
role, including the application's own. Production additionally grants the application role
only INSERT/SELECT on aud_entries (infra/terraform), so two independent controls must fail.

Revision ID: ed9f2c4c9a5c
Revises: 138e4eb4bf76
Create Date: 2026-10-14 14:15:03.418072
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ed9f2c4c9a5c"
down_revision: str | None = "138e4eb4bf76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "aud_entries",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_role", sa.String(length=16), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_aud_entries")),
        sa.UniqueConstraint("hash", name=op.f("uq_aud_entries_hash")),
    )
    op.create_index(
        "ix_aud_entries_actor_time", "aud_entries", ["actor_id", "occurred_at"], unique=False
    )
    op.create_index(
        "ix_aud_entries_patient_time", "aud_entries", ["patient_id", "occurred_at"], unique=False
    )
    op.create_table(
        "pat_patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("identity_code_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("identity_code_index", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pat_patients")),
        sa.UniqueConstraint(
            "identity_code_index", name=op.f("uq_pat_patients_identity_code_index")
        ),
    )
    op.execute(
        """
        CREATE FUNCTION aud_reject_modification() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'aud_entries is append-only (% rejected)', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER aud_entries_no_update_delete
            BEFORE UPDATE OR DELETE ON aud_entries
            FOR EACH ROW EXECUTE FUNCTION aud_reject_modification();

        CREATE TRIGGER aud_entries_no_truncate
            BEFORE TRUNCATE ON aud_entries
            FOR EACH STATEMENT EXECUTE FUNCTION aud_reject_modification();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER aud_entries_no_truncate ON aud_entries")
    op.execute("DROP TRIGGER aud_entries_no_update_delete ON aud_entries")
    op.execute("DROP FUNCTION aud_reject_modification()")
    op.drop_table("pat_patients")
    op.drop_index("ix_aud_entries_patient_time", table_name="aud_entries")
    op.drop_index("ix_aud_entries_actor_time", table_name="aud_entries")
    op.drop_table("aud_entries")
