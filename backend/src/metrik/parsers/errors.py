"""Exceções tipadas do pipeline de parsing (ver docs/specs/parser-inbody.md)."""

from __future__ import annotations


class ParserError(Exception):
    """Base para todas as exceções de parsing de laudos."""


class PDFNaoTextualError(ParserError):
    """PDF sem texto extraível (provável scan/imagem) ou corrompido."""


class LayoutInesperadoError(ParserError):
    """Página 1 não bate com o template esperado.

    ``campos_faltantes`` lista os campos obrigatórios que não foram
    localizados na posição esperada.
    """

    def __init__(self, mensagem: str, campos_faltantes: list[str]) -> None:
        super().__init__(mensagem)
        self.campos_faltantes = campos_faltantes


class FormatoValorInvalidoError(ParserError):
    """Um valor foi localizado mas não pôde ser convertido para número."""

    def __init__(self, mensagem: str, campo: str, valor_bruto: str) -> None:
        super().__init__(mensagem)
        self.campo = campo
        self.valor_bruto = valor_bruto
