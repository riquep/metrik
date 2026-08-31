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
pip install -e ".[dev]"
uvicorn dev_harness.main:app --reload
```

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre em `http://localhost:5173`.

## URL do backend

Por padrão o frontend chama `http://localhost:8000`. Pra apontar pra
outro backend (ex: o backend publicado na Vercel), defina
`VITE_BACKEND_URL` — veja `.env.example`. Localmente, copie pra `.env`:

```bash
cp .env.example .env
# edite VITE_BACKEND_URL em .env
```

No projeto `metrik_front` na Vercel, defina `VITE_BACKEND_URL` em
Settings → Environment Variables com a URL do projeto `metrik_api` (ex:
`https://metrik-ezekcdcpd-riqueps-projects.vercel.app`) e redeploy o
frontend — variáveis `VITE_*` são embutidas no build, então mudar o valor
exige um novo build, não só reiniciar.
