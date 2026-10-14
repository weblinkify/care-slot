"""Scheduling tables: clinics, clinicians, slots, appointments.

Revision ID: 138e4eb4bf76
Revises:
Create Date: 2026-10-14 13:49:46.891022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "138e4eb4bf76"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sched_clinics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sched_clinics")),
    )
    op.create_table(
        "sched_clinicians",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("specialty", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["sched_clinics.id"],
            name=op.f("fk_sched_clinicians_clinic_id_sched_clinics"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sched_clinicians")),
    )
    op.create_index(
        op.f("ix_sched_clinicians_clinic_id"), "sched_clinicians", ["clinic_id"], unique=False
    )
    op.create_table(
        "sched_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("clinician_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name=op.f("ck_sched_slots_positive_duration")),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["sched_clinicians.id"],
            name=op.f("fk_sched_slots_clinician_id_sched_clinicians"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sched_slots")),
    )
    op.create_index(
        "ix_sched_slots_clinician_start", "sched_slots", ["clinician_id", "starts_at"], unique=False
    )
    op.create_table(
        "sched_appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("clinician_id", sa.Uuid(), nullable=False),
        sa.Column("slot_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('booked', 'cancelled')", name=op.f("ck_sched_appointments_valid_status")
        ),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["sched_clinicians.id"],
            name=op.f("fk_sched_appointments_clinician_id_sched_clinicians"),
        ),
        sa.ForeignKeyConstraint(
            ["slot_id"], ["sched_slots.id"], name=op.f("fk_sched_appointments_slot_id_sched_slots")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sched_appointments")),
    )
    op.create_index(
        "ix_sched_appointments_clinician_start",
        "sched_appointments",
        ["clinician_id", "starts_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sched_appointments_patient_id"), "sched_appointments", ["patient_id"], unique=False
    )
    op.create_index(
        "uq_sched_appointments_active_slot",
        "sched_appointments",
        ["slot_id"],
        unique=True,
        postgresql_where=sa.text("status = 'booked'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_sched_appointments_active_slot",
        table_name="sched_appointments",
        postgresql_where=sa.text("status = 'booked'"),
    )
    op.drop_index(op.f("ix_sched_appointments_patient_id"), table_name="sched_appointments")
    op.drop_index("ix_sched_appointments_clinician_start", table_name="sched_appointments")
    op.drop_table("sched_appointments")
    op.drop_index("ix_sched_slots_clinician_start", table_name="sched_slots")
    op.drop_table("sched_slots")
    op.drop_index(op.f("ix_sched_clinicians_clinic_id"), table_name="sched_clinicians")
    op.drop_table("sched_clinicians")
    op.drop_table("sched_clinics")
