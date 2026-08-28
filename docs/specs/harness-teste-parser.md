# Spec: Harness de Teste Manual — Upload + Extração (DESCARTÁVEL)

## ⚠️ Este código é temporário
Objetivo único: permitir testar visualmente o parser (`docs/specs/parser-inbody.md`)
fazendo upload de um PDF real e vendo o JSON extraído na tela, sem depender de
autenticação, banco de dados, ou modelo de clínica/paciente.

Este código **não** deve:
- Ganhar autenticação, persistência em banco, ou qualquer lógica de negócio.
- Ser usado como base pro dashboard real do paciente (que vem depois, na
  spec de fundação + dashboard).
- Ficar em produção — é ferramenta de desenvolvimento.

Quando a etapa de fundação (auth + multi-tenancy + modelo de dados) e o
upload pipeline real existirem, este harness deve ser removido do repositório
(ou movido pra uma pasta claramente marcada como `/dev-tools`, fora do build
de produção).

## Backend — endpoint único

`POST /dev/parse` (prefixo `/dev/` sinaliza que não é rota de produto)
- Recebe um PDF via multipart/form-data.
- Chama o parser já implementado (`parser-inbody.md`).
- Retorna o JSON de saída diretamente na resposta — sucesso ou erro.
- Em caso de erro do parser (`PDFNaoTextualError`, `LayoutInesperadoError`,
  `FormatoValorInvalidoError`), retorna HTTP 422 com `{ "error": "<tipo>", "message": "<detalhe>" }`.
- Sem autenticação. Sem gravação em banco. Arquivo recebido é descartado após
  a resposta (não salvar em disco).

## Frontend — página única

Uma página HTML/React simples, sem rota protegida, sem navegação:
- Um `<input type="file" accept="application/pdf">`.
- Botão "Extrair dados".
- Ao enviar, chama `POST /dev/parse` e exibe o resultado:
  - Se sucesso: tabela simples com `key | value | unit | ref_min | ref_max`
    (uma linha por métrica), mais os campos de `evaluation` (data, aparelho,
    biometria) no topo.
  - Se erro: mostra a mensagem de erro de forma legível (tipo do erro +
    detalhe), não só o JSON cru do erro.
- Sem estilização elaborada — funcional, não bonito. Não reutilizar
  componentes do dashboard final (esses ainda não existem).

## Critérios de aceite
- [ ] Sobe um PDF real do InBody370S e vê o JSON/tabela extraída na tela.
- [ ] Sobe um PDF que não é do InBody (ou um arquivo corrompido) e vê uma
      mensagem de erro clara, não uma tela quebrada ou erro 500 genérico.
- [ ] Não grava nada em disco nem em banco — cada upload é stateless.
- [ ] Fácil de rodar localmente com um único comando (documentar no próprio
      README da pasta, ex: `uvicorn dev_harness.main:app --reload` +
      `npm run dev`).
