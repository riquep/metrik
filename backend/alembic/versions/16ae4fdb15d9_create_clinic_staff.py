"""create clinic_staff

Revision ID: 16ae4fdb15d9
Revises: 8d62917968f4
Create Date: 2026-09-02 20:50:58.479545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '16ae4fdb15d9'
down_revision: Union[str, Sequence[str], None] = '8d62917968f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "clinic_staff",
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
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="operador"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("email", name="uq_clinic_staff_email"),
    )

    op.execute("ALTER TABLE clinic_staff ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE clinic_staff FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY clinic_isolation ON clinic_staff
          USING (clinic_id = current_setting('app.current_clinic_id')::uuid)
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON clinic_staff TO metrik_app")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE ALL ON clinic_staff FROM metrik_app")
    op.drop_table("clinic_staff")
