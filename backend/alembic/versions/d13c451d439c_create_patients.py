"""create patients

Revision ID: d13c451d439c
Revises: 16ae4fdb15d9
Create Date: 2026-09-02 20:50:58.9

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd13c451d439c'
down_revision: Union[str, Sequence[str], None] = '16ae4fdb15d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "patients",
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
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("cpf", sa.Text(), nullable=False),
        sa.Column("invite_status", sa.Text(), nullable=False, server_default="pendente"),
        sa.Column("account_activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("clinic_id", "cpf", name="uq_patients_clinic_cpf"),
    )
    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"])

    op.execute("ALTER TABLE patients ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE patients FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY clinic_isolation ON patients
          USING (clinic_id = current_setting('app.current_clinic_id')::uuid)
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON patients TO metrik_app")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE ALL ON patients FROM metrik_app")
    op.drop_index("ix_patients_clinic_id", table_name="patients")
    op.drop_table("patients")
