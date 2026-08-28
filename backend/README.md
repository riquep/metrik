# backend

Parsers de laudos de bioimpedância (`src/metrik/`) + harness de teste manual
descartável (`src/dev_harness/`).

## Setup

```bash
cd backend
pip install -e ".[dev,harness]"
```

## Rodar os testes

```bash
pytest
```

## Rodar o harness de teste manual (⚠️ descartável)

Ver `docs/specs/harness-teste-parser.md` — ferramenta de desenvolvimento
para testar o parser InBody370S subindo um PDF real e vendo o JSON
extraído. Sem autenticação, sem persistência; deve ser removida quando a
fundação (auth + multi-tenancy + modelo de dados) existir.

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
