import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from metrik.db.base import tenant_session
from metrik.db.models import Clinic, Evaluation, Metric, Patient


@pytest.fixture
def clinic(admin_session_factory) -> Clinic:
    clinic = Clinic(id=uuid.uuid4(), nome="Clínica Teste", cnpj="33.333.333/0001-33")
    with admin_session_factory() as session:
        session.add(clinic)
        session.commit()
        session.refresh(clinic)
    return clinic


@pytest.fixture
def other_clinic(admin_session_factory) -> Clinic:
    clinic = Clinic(id=uuid.uuid4(), nome="Outra Clínica", cnpj="44.444.444/0001-44")
    with admin_session_factory() as session:
        session.add(clinic)
        session.commit()
        session.refresh(clinic)
    return clinic


def test_cpf_duplicado_na_mesma_clinica_falha(app_session_factory, clinic: Clinic) -> None:
    with tenant_session(clinic.id, app_session_factory) as session:
        session.add(
            Patient(
                id=uuid.uuid4(), clinic_id=clinic.id, nome="Paciente 1",
                email="p1@example.com", cpf="123.456.789-00",
            )
        )

    with pytest.raises(IntegrityError, match="uq_patients_clinic_cpf"):
        with tenant_session(clinic.id, app_session_factory) as session:
            session.add(
                Patient(
                    id=uuid.uuid4(), clinic_id=clinic.id, nome="Paciente 1 de novo",
                    email="p1b@example.com", cpf="123.456.789-00",
                )
            )


def test_mesmo_cpf_em_clinica_diferente_funciona(
    app_session_factory, clinic: Clinic, other_clinic: Clinic
) -> None:
    with tenant_session(clinic.id, app_session_factory) as session:
        session.add(
            Patient(
                id=uuid.uuid4(), clinic_id=clinic.id, nome="Paciente 1",
                email="p1@example.com", cpf="123.456.789-00",
            )
        )

    with tenant_session(other_clinic.id, app_session_factory) as session:
        session.add(
            Patient(
                id=uuid.uuid4(), clinic_id=other_clinic.id, nome="Paciente 1 na outra clínica",
                email="p1@outra.example.com", cpf="123.456.789-00",
            )
        )
    # chegar até aqui sem exceção já é a asserção: mesmo CPF, clínica diferente, sem conflito.


def test_metrica_duplicada_na_mesma_avaliacao_falha(
    app_session_factory, clinic: Clinic
) -> None:
    evaluation_id = uuid.uuid4()

    with tenant_session(clinic.id, app_session_factory) as session:
        patient = Patient(
            id=uuid.uuid4(), clinic_id=clinic.id, nome="Paciente",
            email="p@example.com", cpf="999.999.999-99",
        )
        session.add(patient)
        session.flush()

        session.add(
            Evaluation(
                id=evaluation_id, clinic_id=clinic.id, patient_id=patient.id,
                measured_at=datetime.now(timezone.utc), device_model="InBody370S",
                pdf_storage_key="x.pdf", parser_version="inbody370s-v1", status="processado",
            )
        )
        session.flush()
        session.add(
            Metric(id=uuid.uuid4(), clinic_id=clinic.id, evaluation_id=evaluation_id,
                   key="peso", value=70.0, unit="kg", ref_min=None, ref_max=None)
        )

    with pytest.raises(IntegrityError, match="uq_metrics_evaluation_key"):
        with tenant_session(clinic.id, app_session_factory) as session:
            session.add(
                Metric(id=uuid.uuid4(), clinic_id=clinic.id, evaluation_id=evaluation_id,
                       key="peso", value=71.0, unit="kg", ref_min=None, ref_max=None)
            )
