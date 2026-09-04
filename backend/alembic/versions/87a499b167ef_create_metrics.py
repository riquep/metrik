"""create metrics

Revision ID: 87a499b167ef
Revises: f48d7d6a97ba
Create Date: 2026-09-02 20:50:59.5

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '87a499b167ef'
down_revision: Union[str, Sequence[str], None] = 'f48d7d6a97ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "metrics",
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
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("ref_min", sa.Numeric(), nullable=True),
        sa.Column("ref_max", sa.Numeric(), nullable=True),
        sa.UniqueConstraint("evaluation_id", "key", name="uq_metrics_evaluation_key"),
        # FK composta: garante que evaluation_id pertence à mesma clinic_id
        # desta métrica — evaluations tem uq_evaluations_clinic_id_id.
        sa.ForeignKeyConstraint(
            ["clinic_id", "evaluation_id"],
            ["evaluations.clinic_id", "evaluations.id"],
            name="fk_metrics_clinic_evaluation",
        ),
    )
    op.create_index("ix_metrics_evaluation_id", "metrics", ["evaluation_id"])

    op.execute("ALTER TABLE metrics ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE metrics FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY clinic_isolation ON metrics
          USING (clinic_id = current_setting('app.current_clinic_id')::uuid)
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON metrics TO metrik_app")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE ALL ON metrics FROM metrik_app")
    op.drop_index("ix_metrics_evaluation_id", table_name="metrics")
    op.drop_table("metrics")
