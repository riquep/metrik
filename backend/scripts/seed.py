"""Popula dados de desenvolvimento: 2 clínicas, alguns pacientes e avaliações.

As avaliações/métricas de um dos pacientes vêm dos golden JSON reais do
parser (`backend/tests/fixtures/inbody370s/*.expected.json`) — dado
realista de verdade, em vez de números inventados.

Uso:
    cd backend
    ADMIN_DATABASE_URL=... APP_DATABASE_URL=... python scripts/seed.py
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from metrik.db.base import make_engine, make_session_factory, tenant_session
from metrik.db.models import Clinic, ClinicStaff, Evaluation, Metric, Patient

FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "inbody370s"
FIXTURE_FILES = ["250320", "251002", "260827"]


def _create_clinics(session_factory) -> list[Clinic]:
    clinics = [
        Clinic(id=uuid.uuid4(), nome="Clínica ProNutro", cnpj="11.111.111/0001-11"),
        Clinic(id=uuid.uuid4(), nome="Clínica Vitalis", cnpj="22.222.222/0001-22"),
    ]
    with session_factory() as session:
        session.add_all(clinics)
        session.commit()
        for clinic in clinics:
            session.refresh(clinic)
    return clinics


def _seed_clinic_a(session_factory, clinic: Clinic) -> None:
    with tenant_session(clinic.id, session_factory) as session:
        session.add(
            ClinicStaff(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                email="admin@pronutro.example",
                nome="Ana Diretora",
                password_hash="placeholder-hash",
                role="admin",
            )
        )

        patient_with_history = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            nome="Henrique Pauli",
            email="henrique@example.com",
            cpf="000.000.001-00",
            invite_status="ativo",
            account_activated_at=datetime.now(timezone.utc),
        )
        patient_no_evaluations = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            nome="Beatriz Souza",
            email="beatriz@example.com",
            cpf="000.000.002-00",
            invite_status="pendente",
        )
        session.add_all([patient_with_history, patient_no_evaluations])
        session.flush()

        for name in FIXTURE_FILES:
            golden = json.loads((FIXTURES_DIR / f"{name}.expected.json").read_text())
            evaluation = Evaluation(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                patient_id=patient_with_history.id,
                measured_at=datetime.fromisoformat(golden["evaluation"]["measured_at"]),
                device_model=golden["evaluation"]["device_model"],
                pdf_storage_key=f"inbody370s/{name}.pdf",
                parser_version=golden["raw_extraction"]["parser_version"],
                status="processado" if golden["raw_extraction"]["confidence"] == "ok" else "suspeito",
            )
            session.add(evaluation)
            session.flush()
            for metric in golden["metrics"]:
                session.add(
                    Metric(
                        id=uuid.uuid4(),
                        clinic_id=clinic.id,
                        evaluation_id=evaluation.id,
                        key=metric["key"],
                        value=metric["value"],
                        unit=metric["unit"],
                        ref_min=metric["ref_min"],
                        ref_max=metric["ref_max"],
                    )
                )


def _seed_clinic_b(session_factory, clinic: Clinic) -> None:
    with tenant_session(clinic.id, session_factory) as session:
        session.add(
            ClinicStaff(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                email="admin@vitalis.example",
                nome="Vitor Nogueira",
                password_hash="placeholder-hash",
                role="admin",
            )
        )

        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            nome="Carla Mendes",
            email="carla@example.com",
            cpf="000.000.003-00",
            invite_status="ativo",
            account_activated_at=datetime.now(timezone.utc),
        )
        session.add(patient)
        session.flush()

        evaluation = Evaluation(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            patient_id=patient.id,
            measured_at=datetime.now(timezone.utc) - timedelta(days=3),
            device_model="InBody370S",
            pdf_storage_key="inbody370s/exemplo-vitalis.pdf",
            parser_version="inbody370s-v1",
            status="processado",
        )
        session.add(evaluation)
        session.flush()
        session.add(
            Metric(
                id=uuid.uuid4(),
                clinic_id=clinic.id,
                evaluation_id=evaluation.id,
                key="peso",
                value=68.4,
                unit="kg",
                ref_min=52.0,
                ref_max=68.0,
            )
        )


def main() -> None:
    engine = make_engine()
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT count(*) FROM clinics")).scalar_one()
    if existing:
        print(f"Já existem {existing} clínica(s) — abortando pra não duplicar seed.", file=sys.stderr)
        print("Rode `alembic downgrade base && alembic upgrade head` pra recomeçar do zero.", file=sys.stderr)
        raise SystemExit(1)

    session_factory = make_session_factory(engine)
    clinic_a, clinic_b = _create_clinics(session_factory)
    _seed_clinic_a(session_factory, clinic_a)
    _seed_clinic_b(session_factory, clinic_b)

    print(f"Clínica A (ProNutro): {clinic_a.id}")
    print(f"Clínica B (Vitalis):  {clinic_b.id}")
    print("Seed concluído.")


if __name__ == "__main__":
    main()
