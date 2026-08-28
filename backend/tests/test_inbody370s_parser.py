import json
from pathlib import Path

import pytest

from metrik.parsers.errors import LayoutInesperadoError, PDFNaoTextualError
from metrik.parsers.inbody370s import InBody370SParser

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "inbody370s"

GOLDEN_FIXTURES = ["250320", "251002", "260827"]


@pytest.fixture
def parser() -> InBody370SParser:
    return InBody370SParser()


@pytest.mark.parametrize("nome", GOLDEN_FIXTURES)
def test_parse_produz_json_esperado(parser: InBody370SParser, nome: str) -> None:
    pdf_path = FIXTURES_DIR / f"{nome}.pdf"
    golden_path = FIXTURES_DIR / f"{nome}.expected.json"

    resultado = parser.parse(pdf_path).to_dict()
    esperado = json.loads(golden_path.read_text())

    assert resultado == esperado


def test_pdf_corrompido_lanca_pdf_nao_textual_error(parser: InBody370SParser) -> None:
    with pytest.raises(PDFNaoTextualError):
        parser.parse(FIXTURES_DIR / "corrupted.pdf")


def test_layout_inesperado_lanca_erro_com_campos_faltantes(
    parser: InBody370SParser,
) -> None:
    with pytest.raises(LayoutInesperadoError) as exc_info:
        parser.parse(FIXTURES_DIR / "layout_inesperado.pdf")

    assert exc_info.value.campos_faltantes
    assert "peso" in exc_info.value.campos_faltantes
