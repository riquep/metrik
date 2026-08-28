# frontend

Página única do harness de teste manual descartável (ver
`docs/specs/harness-teste-parser.md`): upload de um PDF do InBody370S,
mostra o JSON/tabela extraída. Sem autenticação, sem rotas, sem
componentes do dashboard real (que ainda não existe). Deve ser removida
quando a fundação real existir.

## Rodar

Precisa do backend rodando em `http://localhost:8000` (ver
`../backend/README.md`):

```bash
cd backend
pip install -e ".[dev,harness]"
uvicorn dev_harness.main:app --reload
```

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre em `http://localhost:5173`.
