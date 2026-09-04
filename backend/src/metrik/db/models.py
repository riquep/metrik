"""Modelo de dados multi-tenant (ver docs/specs/modelo-dados-multitenancy.md).

Isolamento entre clínicas é feito por Row-Level Security no Postgres (ver
migrations em ``backend/alembic/versions/``), não só por filtro aqui na
camada de ORM — os modelos abaixo declaram `clinic_id` explicitamente porque
a policy de RLS depende dessa coluna existir em cada tabela, mas nenhuma
query feita através da app deve confiar em lembrar de filtrar por
`clinic_id` manualmente.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    nome: Mapped[str] = mapped_column(nullable=False)
    cnpj: Mapped[str] = mapped_column(unique=True, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default="ativa")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )


class ClinicStaff(Base):
    __tablename__ = "clinic_staff"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(nullable=False)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(nullable=False, server_default="operador")
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("clinic_id", "cpf", name="uq_patients_clinic_cpf"),
        # Exigida pelo Postgres pra permitir FKs compostas (clinic_id, patient_id)
        # de evaluations/invites — sem isso nada impede uma sessão da clínica A
        # inserir uma linha com clinic_id=A mas patient_id de um paciente da
        # clínica B (a checagem de FK roda com privilégio interno, ignora RLS).
        UniqueConstraint("clinic_id", "id", name="uq_patients_clinic_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    nome: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False)
    cpf: Mapped[str] = mapped_column(nullable=False)
    invite_status: Mapped[str] = mapped_column(nullable=False, server_default="pendente")
    account_activated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    evaluations: Mapped[list["Evaluation"]] = relationship(back_populates="patient")


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        # FK composta (não só patient_id -> patients.id): garante que o
        # patient_id referenciado pertence à MESMA clinic_id desta linha —
        # ver Patient.__table_args__.
        ForeignKeyConstraint(
            ["clinic_id", "patient_id"],
            ["patients.clinic_id", "patients.id"],
            name="fk_evaluations_clinic_patient",
        ),
        UniqueConstraint("clinic_id", "id", name="uq_evaluations_clinic_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(nullable=False)
    device_model: Mapped[str] = mapped_column(nullable=False)
    pdf_storage_key: Mapped[str] = mapped_column(nullable=False)
    parser_version: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    patient: Mapped["Patient"] = relationship(back_populates="evaluations")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="evaluation")


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "key", name="uq_metrics_evaluation_key"),
        # FK composta: garante que evaluation_id pertence à mesma clinic_id
        # desta métrica — ver Evaluation.__table_args__.
        ForeignKeyConstraint(
            ["clinic_id", "evaluation_id"],
            ["evaluations.clinic_id", "evaluations.id"],
            name="fk_metrics_clinic_evaluation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    evaluation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    key: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit: Mapped[str | None] = mapped_column(nullable=True)
    ref_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    ref_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    evaluation: Mapped["Evaluation"] = relationship(back_populates="metrics")


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        # FK composta: garante que patient_id pertence à mesma clinic_id
        # deste convite — ver Patient.__table_args__.
        ForeignKeyConstraint(
            ["clinic_id", "patient_id"],
            ["patients.clinic_id", "patients.id"],
            name="fk_invites_clinic_patient",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinics.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    token: Mapped[str] = mapped_column(unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
