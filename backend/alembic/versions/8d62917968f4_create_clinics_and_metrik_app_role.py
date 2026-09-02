"""create clinics and metrik_app role

Revision ID: 8d62917968f4
Revises:
Create Date: 2026-09-02 20:50:57.981709

"""
import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8d62917968f4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Senha de dev por padrão — em produção, defina METRIK_APP_DB_PASSWORD no
# ambiente que roda a migration (o valor não fica em nenhum output do
# alembic). Rotacionar depois exige ALTER ROLE fora do controle de versão.
_APP_ROLE_PASSWORD = os.environ.get("METRIK_APP_DB_PASSWORD", "metrik_app_dev_pw")


def upgrade() -> None:
    """Upgrade schema."""
    escaped_password = _APP_ROLE_PASSWORD.replace("'", "''")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'metrik_app') THEN
                CREATE ROLE metrik_app WITH LOGIN PASSWORD '{escaped_password}';
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO metrik_app")

    op.create_table(
        "clinics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("cnpj", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="ativa"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("cnpj", name="uq_clinics_cnpj"),
    )
    # clinics não tem clinic_id (é a própria unidade de tenant) — não faz
    # parte da lista de tabelas com RLS na spec.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON clinics TO metrik_app")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("REVOKE ALL ON clinics FROM metrik_app")
    op.drop_table("clinics")
    op.execute("REVOKE USAGE ON SCHEMA public FROM metrik_app")
    # Não faz DROP ROLE metrik_app: roles são objetos globais do cluster
    # Postgres, não do banco — outro banco no mesmo cluster (ex: metrik_test
    # vs. metrik) pode ter grants concedidos a esse role, e o DROP falharia
    # (ou pior, derrubaria acesso de outro banco). Ficar sem uso após o
    # REVOKE acima é suficiente; remover o role de fato é operação de infra,
    # fora do escopo de uma migration.
