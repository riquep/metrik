# Spec: Parser de PDF de Bioimpedância (InBody370S)

## Objetivo
Extrair, de forma determinística e confiável, os dados de uma avaliação de
bioimpedância em PDF (aparelho InBody370S) e produzir um JSON estruturado que
alimente as tabelas `Evaluation` e `Metric`.

Este módulo é **isolado**: não depende de banco de dados, autenticação, ou do
restante do app. Recebe um caminho de PDF, devolve um JSON (ou lança um erro
tipado). Isso permite testá-lo e validá-lo antes de qualquer outra parte do
sistema existir.

## Fora de escopo (v1)
- Suporte a outros aparelhos/fabricantes (Tanita, Omron etc.) — arquitetura deve
  permitir adicionar novos parsers no futuro (ver "Extensibilidade"), mas a
  implementação v1 cobre só InBody370S.
- Uso do histórico embutido nas páginas 2-3 do PDF (até 15 avaliações
  anteriores). Extrai-se apenas a página 1 (avaliação atual). Ver "Notas para
  o futuro".
- OCR — os PDFs de entrada são sempre texto selecionável, não imagem
  escaneada. Se um PDF vier sem texto extraível, deve falhar explicitamente
  (não tentar OCR).

## Entrada
- Um arquivo PDF de 4 páginas gerado pelo InBody370S.
- Página 1: dados da avaliação atual (fonte de verdade para extração).
- Página 2-3: histórico embutido do aparelho (ignoradas nesta versão).
- Página 4: texto educativo fixo (ignorada).

## Saída — Schema JSON

```json
{
  "evaluation": {
    "device_model": "InBody370S",
    "measured_at": "2026-08-27T15:01:00",
    "patient_ref": { "device_id": "200325-4" },
    "biometrics": { "altura_cm": 178, "idade": 40, "sexo": "M" }
  },
  "metrics": [
    { "key": "peso", "value": 90.3, "unit": "kg", "ref_min": 59.2, "ref_max": 80.2 },
    { "key": "imc", "value": 28.5, "unit": "kg/m2", "ref_min": null, "ref_max": null },
    { "key": "pgc", "value": 22.4, "unit": "%", "ref_min": null, "ref_max": null },
    { "key": "massa_muscular_esqueletica", "value": 39.5, "unit": "kg", "ref_min": null, "ref_max": null },
    { "key": "massa_gordura", "value": 20.3, "unit": "kg", "ref_min": 8.4, "ref_max": 16.7 },
    { "key": "agua_corporal_total", "value": 51.5, "unit": "L", "ref_min": 39.2, "ref_max": 47.8 },
    { "key": "taxa_metabolica_basal", "value": 1883, "unit": "kcal", "ref_min": 1862, "ref_max": 2194 },
    { "key": "gordura_visceral", "value": 9, "unit": "nivel", "ref_min": 1, "ref_max": 9 },
    { "key": "relacao_cintura_quadril", "value": 0.93, "unit": null, "ref_min": 0.80, "ref_max": 0.90 },
    { "key": "pontuacao_inbody", "value": 83, "unit": "pontos", "ref_min": null, "ref_max": null }
  ],
  "raw_extraction": {
    "parser_version": "inbody370s-v1",
    "confidence": "ok",
    "warnings": []
  }
}
```

Regras do schema:
- `metrics[].key` usa sempre os nomes canônicos definidos nesta spec (não o
  texto literal do PDF, que pode ter variações de acentuação/abreviação).
- Campos sem faixa de referência no PDF usam `ref_min`/`ref_max` como `null`,
  nunca omitidos (facilita consumo previsível a jusante).
- `raw_extraction.confidence` é `"ok"` ou `"suspeito"` (ver Validação abaixo).
- `raw_extraction.warnings` lista strings legíveis quando algo foi extraído
  mas ficou fora do esperado (ver Validação).

## Estratégia de extração
- Usar `pdfplumber` (ou equivalente) para extrair **palavras com posição
  (bounding box)** na página 1 — não o texto corrido. O layout do InBody é
  posicional (x, y), então rótulo e valor não vêm necessariamente em sequência
  no texto extraído bruto.
- Casar rótulo → valor por proximidade posicional (mesma linha / coluna
  esperada), com coordenadas de referência fixadas a partir dos 3 PDFs de
  exemplo (mesmo template, mesmo fabricante).
- Números no formato brasileiro (`90,3`) devem ser convertidos para float
  (`90.3`) — atenção especial aqui, é uma fonte clássica de erro silencioso.

## Validação (obrigatória, não opcional)
Dado de saúde não pode ser gravado silenciosamente se a extração falhar de
forma sutil. Após extrair cada métrica, o parser deve checar plausibilidade
fisiológica básica, por exemplo:
- `peso`: entre 20 e 300 kg
- `altura_cm`: entre 100 e 250 cm
- `pgc` (% gordura corporal): entre 3 e 70
- `imc`: entre 10 e 80

Se qualquer métrica sair da faixa plausível:
- O valor **ainda é incluído** no JSON (não descartar dado),
- `raw_extraction.confidence` vira `"suspeito"`,
- Um warning descritivo é adicionado (ex: `"peso fora da faixa plausível: 903.0 kg — possível erro de parsing de vírgula/ponto"`).
- A decisão de bloquear ou não o registro (`status = erro` vs `processado`)
  fica para a camada de integração (fora desta spec), não para o parser.

## Tratamento de erro
O parser deve lançar exceções tipadas e específicas, não genéricas:
- `PDFNaoTextualError` — PDF sem texto extraível (provável scan/imagem).
- `LayoutInesperadoError` — página 1 não bate com o template esperado (ex:
  campo obrigatório não encontrado na posição esperada). Deve incluir no erro
  quais campos não foram localizados.
- `FormatoValorInvalidoError` — um valor foi localizado mas não pôde ser
  convertido para número.

Nenhum desses erros deve ser silenciado; a função principal do parser deve
deixá-los propagar para quem chamou.

## Critérios de aceite
- [ ] Roda com os 3 PDFs de exemplo (anonimizados) e produz JSON correto,
      validado campo a campo manualmente uma vez.
- [ ] Testes de regressão automatizados usando os 3 PDFs como fixtures
      (comparar contra JSON esperado congelado).
- [ ] Teste com um PDF corrompido/vazio → `PDFNaoTextualError`.
- [ ] Teste com um PDF de outro layout (ex: página 1 editada/faltando campo)
      → `LayoutInesperadoError` com a lista de campos faltantes.
- [ ] Nenhuma dependência de rede, banco de dados, ou variável de ambiente de
      produção para rodar os testes.
- [ ] `parser_version` incrementa sempre que a lógica de extração mudar, para
      permitir re-processar avaliações antigas se necessário.

## Fixtures de teste
- 3 PDFs reais do InBody370S, **anonimizados antes de entrar no repositório**
  (remover nome do paciente e ID do aparelho, manter os valores numéricos).
- Local sugerido: `/backend/tests/fixtures/inbody370s/`.
- Cada fixture acompanhada do JSON esperado congelado (golden file).

## Notas para o futuro (não implementar agora)
- Suporte a múltiplos fabricantes: desenhar a interface do parser (`parse(pdf_path) -> EvaluationData`)
  de forma que trocar de aparelho seja implementar uma nova classe, não reescrever o pipeline.
- Uso do histórico embutido (páginas 2-3) como importação retroativa em lote,
  útil quando uma clínica migra para a plataforma e quer trazer o passado.
