"""create evaluations

Revision ID: f48d7d6a97ba
Revises: d13c451d439c
Create Date: 2026-09-02 20:50:59.2

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f48d7d6a97ba'
down_revision: Union[str, Sequence[str], None] = 'd13c451d439c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "evaluations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "clinic_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clinics.id"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=False,
        ),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_model", sa.Text(), nullable=False),
        sa.Column("pdf_storage_key", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_evaluations_clinic_patient_measured_at",
        "evaluations",
        ["clinic_id", "patient_id", sa.text("measured_at DESC")],
    )

    op.execute("ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE evaluations FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY clinic_isolation ON evaluations
          USING (clinic_id = current_setting('app.current_clinic_id')::uuid)
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON evaluations TO metrik_app")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE ALL ON evaluations FROM metrik_app")
    op.drop_index("ix_evaluations_clinic_patient_measured_at", table_name="evaluations")
    op.drop_table("evaluations")
