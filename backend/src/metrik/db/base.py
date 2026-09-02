"""Engine/sessão do banco + contexto de tenant (`app.current_clinic_id`).

A sessão da aplicação sempre conecta como o role restrito `metrik_app`
(sujeito a RLS — ver migrations), nunca como o role de migration/admin.
Toda operação de banco feita pela aplicação deve passar por
:func:`tenant_session`, que define `app.current_clinic_id` via `SET LOCAL`
(escopo de transação) antes de qualquer query — sem isso, as policies de
RLS não deixam nenhuma linha passar (ver spec, "Row-Level Security").

`SET LOCAL` (em vez de `SET`) é proposital: como as sessões vêm de um pool
de conexões, `SET` vazaria o `clinic_id` de uma sessão pra outra requisição
que reutilize a mesma conexão física depois. Por isso `tenant_session` é
uma transação só: ela abre a transação, define `app.current_clinic_id`,
executa o bloco do chamador e comita (ou desfaz, se der exceção) — não dá
`session.commit()` você mesmo dentro do `with`, ou o `SET LOCAL` deixa de
valer no que rodar depois no mesmo bloco.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

APP_DATABASE_URL_ENV = "APP_DATABASE_URL"
DEFAULT_APP_DATABASE_URL = (
    "postgresql+psycopg://metrik_app:metrik_app_dev_pw@localhost:5432/metrik"
)


def get_app_database_url() -> str:
    return os.environ.get(APP_DATABASE_URL_ENV, DEFAULT_APP_DATABASE_URL)


def make_engine(database_url: str | None = None):
    return create_engine(database_url or get_app_database_url())


def make_session_factory(engine=None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or make_engine())


@contextmanager
def tenant_session(
    clinic_id: uuid.UUID | str, session_factory: sessionmaker[Session] | None = None
) -> Iterator[Session]:
    """Sessão de banco, já dentro de uma transação, com
    `app.current_clinic_id` definido para essa transação.

    Uso:
        with tenant_session(clinic.id) as session:
            session.query(Patient).all()  # só vê pacientes dessa clínica
            session.add(Patient(...))
        # commit automático aqui (ou rollback, se o bloco levantar exceção)

    Não chame `session.commit()`/`session.rollback()` dentro do bloco: isso
    é gerenciado pelo context manager pra garantir que exista só uma
    transação (logo, um `SET LOCAL` válido) do início ao fim do bloco.
    """
    # Postgres não aceita bind parameters em SET/SET LOCAL — validamos que é
    # um UUID de verdade e interpolamos o valor já normalizado, sem risco de
    # injeção (uuid.UUID rejeita qualquer coisa que não seja um UUID válido).
    validated_clinic_id = uuid.UUID(str(clinic_id))

    factory = session_factory or make_session_factory()
    with factory() as session, session.begin():
        session.execute(text(f"SET LOCAL app.current_clinic_id = '{validated_clinic_id}'"))
        yield session
