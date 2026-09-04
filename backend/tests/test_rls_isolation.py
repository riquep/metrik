import uuid
from datetime import datetime, timezone

import pytest

# sqlalchemy só vem com o extra opcional `db` — pula o módulo inteiro (em vez
# de quebrar a collection do pytest) se só `.[dev]` estiver instalado.
pytest.importorskip("sqlalchemy")

from sqlalchemy.exc import ProgrammingError

from metrik.db.base import tenant_session
from metrik.db.models import Clinic, Evaluation, Metric, Patient


@pytest.fixture
def two_clinics_with_data(admin_session_factory):
    """2 clínicas, 1 paciente + 1 avaliação + 1 métrica cada, via role admin
    (superuser, bypassa RLS — só usado pra montar o cenário do teste)."""
    clinic_a = Clinic(id=uuid.uuid4(), nome="Clínica A", cnpj="11.111.111/0001-11")
    clinic_b = Clinic(id=uuid.uuid4(), nome="Clínica B", cnpj="22.222.222/0001-22")

    with admin_session_factory() as session:
        session.add_all([clinic_a, clinic_b])
        session.flush()

        patient_a = Patient(
            id=uuid.uuid4(), clinic_id=clinic_a.id, nome="Paciente A",
            email="a@example.com", cpf="111.111.111-11",
        )
        patient_b = Patient(
            id=uuid.uuid4(), clinic_id=clinic_b.id, nome="Paciente B",
            email="b@example.com", cpf="222.222.222-22",
        )
        session.add_all([patient_a, patient_b])
        session.flush()

        now = datetime.now(timezone.utc)
        evaluation_a = Evaluation(
            id=uuid.uuid4(), clinic_id=clinic_a.id, patient_id=patient_a.id,
            measured_at=now, device_model="InBody370S",
            pdf_storage_key="x.pdf", parser_version="inbody370s-v1", status="processado",
        )
        evaluation_b = Evaluation(
            id=uuid.uuid4(), clinic_id=clinic_b.id, patient_id=patient_b.id,
            measured_at=now, device_model="InBody370S",
            pdf_storage_key="y.pdf", parser_version="inbody370s-v1", status="processado",
        )
        session.add_all([evaluation_a, evaluation_b])
        session.flush()

        session.add_all([
            Metric(id=uuid.uuid4(), clinic_id=clinic_a.id, evaluation_id=evaluation_a.id,
                   key="peso", value=70.0, unit="kg", ref_min=None, ref_max=None),
            Metric(id=uuid.uuid4(), clinic_id=clinic_b.id, evaluation_id=evaluation_b.id,
                   key="peso", value=80.0, unit="kg", ref_min=None, ref_max=None),
        ])
        session.commit()
        session.refresh(clinic_a)
        session.refresh(clinic_b)

    return clinic_a, clinic_b


def test_query_sem_filtro_explicito_so_retorna_a_clinica_do_contexto(
    app_session_factory, two_clinics_with_data
) -> None:
    clinic_a, clinic_b = two_clinics_with_data

    with tenant_session(clinic_a.id, app_session_factory) as session:
        # SELECT * sem where clinic_id=... nenhum: a policy de RLS é quem filtra.
        nomes = {p.nome for p in session.query(Patient).all()}

    assert nomes == {"Paciente A"}


def test_clinica_b_nao_ve_nenhuma_linha_da_clinica_a(
    app_session_factory, two_clinics_with_data
) -> None:
    clinic_a, clinic_b = two_clinics_with_data

    with tenant_session(clinic_b.id, app_session_factory) as session:
        nomes = {p.nome for p in session.query(Patient).all()}
        evaluations = [(e.clinic_id, e.id) for e in session.query(Evaluation).all()]
        valores = [float(m.value) for m in session.query(Metric).all()]

    assert nomes == {"Paciente B"}
    assert len(evaluations) == 1
    assert evaluations[0][0] == clinic_b.id
    assert valores == [80.0]


def test_isolamento_vale_tambem_em_tabela_denormalizada_metrics(
    app_session_factory, two_clinics_with_data
) -> None:
    clinic_a, _clinic_b = two_clinics_with_data

    with tenant_session(clinic_a.id, app_session_factory) as session:
        valores = [float(m.value) for m in session.query(Metric).all()]

    assert valores == [70.0]


def test_sem_contexto_de_tenant_falha_em_vez_de_vazar_dado(
    app_session_factory, two_clinics_with_data
) -> None:
    """Sem `SET app.current_clinic_id`, a policy não tem o que comparar —
    Postgres levanta erro (fail-closed), não retorna todas as linhas."""
    with app_session_factory() as session:
        with pytest.raises(ProgrammingError, match="app.current_clinic_id"):
            session.query(Patient).all()
