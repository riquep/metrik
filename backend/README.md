# backend

Parsers de laudos de bioimpedância (`src/metrik/parsers/`) + modelo de
dados multi-tenant com RLS (`src/metrik/db/`, `alembic/`) + harness de
teste manual descartável (`src/dev_harness/`).

## Setup

```bash
cd backend
pip install -e ".[dev]"        # parser + harness
pip install -e ".[dev,db]"     # + SQLAlchemy/Alembic/psycopg, pra mexer no banco
```

## Rodar os testes

```bash
pytest
```

Os testes de banco (`test_rls_isolation.py`, `test_constraints.py`) são
pulados automaticamente se não houver um Postgres de teste configurado
(ver seção abaixo) — os demais rodam sem banco nenhum.

## Rodar o harness de teste manual (⚠️ descartável)

Ver `docs/specs/harness-teste-parser.md` — ferramenta de desenvolvimento
para testar o parser InBody370S subindo um PDF real e vendo o JSON
extraído. Sem autenticação, sem persistência; deve ser removida quando a
fundação de auth existir (`docs/specs/auth-convite-paciente.md`).

```bash
uvicorn dev_harness.main:app --reload
```

Sobe em `http://localhost:8000`, expõe `POST /dev/parse`. Precisa também do
frontend rodando (ver `../frontend/README.md`, `npm run dev`) para testar
pela UI, ou pode ser testado direto com `curl`:

```bash
curl -F "file=@tests/fixtures/inbody370s/260827.pdf;type=application/pdf" \
  http://localhost:8000/dev/parse
```

## Banco de dados (multi-tenancy + RLS)

Ver `docs/specs/modelo-dados-multitenancy.md`. Schema Postgres com
isolamento entre clínicas via Row-Level Security — a aplicação sempre
conecta com o role restrito `metrik_app` (sujeito a RLS), nunca com o role
de migration/admin.

### Setup local (uma vez)

Criação de databases e do role de migration é infra, não faz parte das
migrations (o role `metrik_app`, esse sim, é criado pela primeira
migration — ver `alembic/versions/..._create_clinics_and_metrik_app_role.py`):

```sql
CREATE ROLE metrik_admin WITH LOGIN PASSWORD 'metrik_admin_dev_pw' CREATEDB SUPERUSER;
CREATE DATABASE metrik OWNER metrik_admin;       -- dev
CREATE DATABASE metrik_test OWNER metrik_admin;  -- usado pelos testes
```

### Rodar migrations

```bash
export ADMIN_DATABASE_URL="postgresql+psycopg://metrik_admin:metrik_admin_dev_pw@localhost:5432/metrik"
alembic upgrade head    # ou: downgrade base / downgrade -1 / etc.
```

### Popular dados de desenvolvimento

```bash
export APP_DATABASE_URL="postgresql+psycopg://metrik_app:metrik_app_dev_pw@localhost:5432/metrik"
python scripts/seed.py
```

Cria 2 clínicas; uma delas com um paciente com histórico de avaliações
reais (os 3 golden JSON de `tests/fixtures/inbody370s/`).

### Rodar os testes de banco

Usam um banco `metrik_test` separado (a suíte reseta o schema
`downgrade base && upgrade head` no início da sessão de testes):

```bash
export TEST_ADMIN_DATABASE_URL="postgresql+psycopg://metrik_admin:metrik_admin_dev_pw@localhost:5432/metrik_test"
export TEST_APP_DATABASE_URL="postgresql+psycopg://metrik_app:metrik_app_dev_pw@localhost:5432/metrik_test"
pytest tests/test_rls_isolation.py tests/test_constraints.py
```

Todas as URLs acima têm os mesmos valores como default nos respectivos
módulos (`metrik.db.base`, `tests/conftest.py`) — só precisa exportar as
variáveis se usar credenciais diferentes das de dev.
