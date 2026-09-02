# Spec: Modelo de Dados + Multi-tenancy (Schema + RLS)

## Objetivo
Definir o schema do banco de dados (PostgreSQL) e o mecanismo de isolamento
entre clínicas (multi-tenancy), servindo de base para todas as features
seguintes (upload pipeline, dashboard, auth).

Este módulo cobre **apenas schema, migrations e políticas de RLS** — não
inclui telas, endpoints de API além dos estritamente necessários pra validar
o isolamento, nem o fluxo de convite (isso é a próxima spec,
`auth-convite-paciente.md`).

## Decisão de arquitetura: banco único + `clinic_id` + Row-Level Security
Um único banco Postgres, com `clinic_id` em toda tabela de dado clínico, e
políticas de RLS enforced pelo próprio Postgres — não apenas por filtro na
camada de aplicação. Isso significa que mesmo uma query malformada ou um bug
na aplicação não deve conseguir retornar dado de outra clínica.

## Tabelas

### `clinics`
| coluna | tipo | notas |
|---|---|---|
| id | uuid, PK | |
| nome | text, not null | |
| cnpj | text, unique, not null | |
| status | text, not null | `ativa` \| `suspensa` — default `ativa` |
| created_at | timestamptz, not null | default `now()` |

### `clinic_staff`
Usuários da clínica que fazem login (quem faz upload, cadastra pacientes).
Separado de `patients` porque tem papel de acesso completamente diferente.

| coluna | tipo | notas |
|---|---|---|
| id | uuid, PK | |
| clinic_id | uuid, FK → clinics.id, not null | |
| email | text, unique, not null | |
| nome | text, not null | |
| password_hash | text, not null | nunca texto plano — ver spec de auth |
| role | text, not null | `admin` \| `operador` — default `operador` |
| created_at | timestamptz, not null | default `now()` |

### `patients`
| coluna | tipo | notas |
|---|---|---|
| id | uuid, PK | |
| clinic_id | uuid, FK → clinics.id, not null | paciente pertence a UMA clínica |
| nome | text, not null | |
| email | text, not null | não único globalmente — mesmo email pode existir em clínicas diferentes |
| cpf | text, not null | usado como identificador humano interno, não exposto em URLs |
| invite_status | text, not null | `pendente` \| `ativo` \| `expirado` — default `pendente` |
| account_activated_at | timestamptz, nullable | preenchido quando o paciente completa o cadastro via convite |
| created_at | timestamptz, not null | default `now()` |

Constraint: `unique (clinic_id, cpf)` — mesmo CPF não pode ser cadastrado
duas vezes na mesma clínica, mas pode existir em clínicas diferentes (ex:
paciente trocou de clínica).

### `evaluations`
| coluna | tipo | notas |
|---|---|---|
| id | uuid, PK | |
| clinic_id | uuid, FK → clinics.id, not null | denormalizado de `patients` — necessário para a policy de RLS funcionar sem join |
| patient_id | uuid, FK → patients.id, not null | |
| measured_at | timestamptz, not null | data/hora da avaliação (do PDF, não do upload) |
| device_model | text, not null | ex: `InBody370S` |
| pdf_storage_key | text, not null | referência ao arquivo original (storage externo, não o binário na tabela) |
| parser_version | text, not null | ex: `inbody370s-v1` — rastreável até a spec do parser |
| status | text, not null | `pendente` \| `processado` \| `suspeito` \| `erro` — ver notas |
| created_at | timestamptz, not null | default `now()` |

Notas sobre `status`:
- `suspeito` corresponde a `raw_extraction.confidence = "suspeito"` do
  parser (valor fora da faixa fisiológica plausível) — o registro existe mas
  fica sinalizado para revisão, não aparece no dashboard do paciente até
  alguém da clínica confirmar.
- `erro` = parser falhou completamente (`LayoutInesperadoError` etc.) —
  nenhuma métrica associada.

### `metrics`
| coluna | tipo | notas |
|---|---|---|
| id | uuid, PK | |
| clinic_id | uuid, FK → clinics.id, not null | denormalizado, mesma razão que em `evaluations` |
| evaluation_id | uuid, FK → evaluations.id, not null | |
| key | text, not null | nome canônico (`peso`, `pgc`, etc — mesmos definidos na spec do parser) |
| value | numeric, not null | |
| unit | text, nullable | |
| ref_min | numeric, nullable | |
| ref_max | numeric, nullable | |

Constraint: `unique (evaluation_id, key)` — uma métrica não se repete dentro
da mesma avaliação.

### `invites`
Tabela separada de `patients` (em vez de campo solto) porque um convite tem
ciclo de vida próprio (pode expirar, pode ser reenviado) e a spec de auth vai
adicionar mais campos aqui.

| coluna | tipo | notas |
|---|---|---|
| id | uuid, PK | |
| clinic_id | uuid, FK → clinics.id, not null | |
| patient_id | uuid, FK → patients.id, not null | |
| token | text, unique, not null | valor aleatório, alta entropia — não sequencial |
| expires_at | timestamptz, not null | |
| used_at | timestamptz, nullable | |
| created_at | timestamptz, not null | default `now()` |

## Índices
- `patients (clinic_id)`
- `evaluations (clinic_id, patient_id, measured_at desc)` — consulta mais
  comum do dashboard: histórico de um paciente ordenado por data.
- `metrics (evaluation_id)`
- `invites (token)` — lookup do convite é sempre por token.

## Row-Level Security (RLS)

Todas as tabelas com `clinic_id` (`patients`, `evaluations`, `metrics`,
`invites`, `clinic_staff`) têm RLS habilitado com uma policy do tipo:

```sql
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;

CREATE POLICY clinic_isolation ON patients
  USING (clinic_id = current_setting('app.current_clinic_id')::uuid);
```

A aplicação define `app.current_clinic_id` no início de cada request/sessão
de banco, a partir do contexto de autenticação (clínica logada, ou clínica do
paciente logado). Nenhuma query deve depender de lembrar de filtrar por
`clinic_id` manualmente — a policy garante isso mesmo se a aplicação
esquecer.

**Exceção:** operações administrativas internas (ex: um painel de suporte da
própria plataforma, se existir no futuro) rodam com um role de banco
separado que faz bypass de RLS — isso não faz parte desta spec, só deixando
registrado que a policy acima não deve ser a única linha de defesa se esse
cenário existir depois.

## Migrations
- Usar a ferramenta de migration do stack escolhido (ex: Alembic, se
  SQLAlchemy no backend).
- Cada tabela acima é uma migration própria, na ordem: `clinics` →
  `clinic_staff` → `patients` → `evaluations` → `metrics` → `invites` (ordem
  de dependência de FK).
- Migrations devem ser reversíveis (`downgrade` implementado, não só
  `upgrade`).

## Critérios de aceite
- [ ] Todas as tabelas acima criadas via migration, com FKs e constraints
      corretos.
- [ ] RLS habilitado e testado: criar 2 clínicas de teste, popular dados em
      ambas, confirmar via teste automatizado que uma sessão com
      `app.current_clinic_id` da clínica A **não retorna nenhuma linha** da
      clínica B, mesmo em query sem filtro explícito de `clinic_id`.
- [ ] Teste de constraint: tentar inserir CPF duplicado na mesma clínica deve
      falhar; o mesmo CPF em clínica diferente deve funcionar.
- [ ] Teste de constraint: tentar inserir métrica duplicada
      (`evaluation_id` + `key` repetidos) deve falhar.
- [ ] Seed script simples para popular dados de desenvolvimento (2 clínicas,
      alguns pacientes, algumas avaliações) — útil para testar o harness de
      upload e, depois, o dashboard.

## Fora de escopo (fica para specs seguintes)
- Endpoints de API para CRUD dessas tabelas (fica para a spec de auth e a de
  upload pipeline).
- Lógica de expiração/reenvio de convite (fica para `auth-convite-paciente.md`).
- Papel de "admin da plataforma" com acesso entre clínicas (mencionado acima
  só como nota, não implementar agora).
