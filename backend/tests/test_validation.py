import pytest

from metrik.parsers.errors import FormatoValorInvalidoError
from metrik.parsers.inbody370s import _parse_leaf, _parse_range
from metrik.parsers.models import Biometrics, Metric
from metrik.parsers.validation import validate


def _biometrics() -> Biometrics:
    return Biometrics(altura_cm=178, idade=40, sexo="M")


def test_validate_confidence_ok_sem_metricas_fora_da_faixa() -> None:
    metrics = [Metric(key="peso", value=90.3, unit="kg", ref_min=59.2, ref_max=80.2)]

    confidence, warnings = validate(_biometrics(), metrics)

    assert confidence == "ok"
    assert warnings == []


def test_validate_marca_suspeito_quando_peso_fora_da_faixa_plausivel() -> None:
    # erro clássico de parsing de vírgula/ponto: "90,3" virou 903.0
    metrics = [Metric(key="peso", value=903.0, unit="kg", ref_min=59.2, ref_max=80.2)]

    confidence, warnings = validate(_biometrics(), metrics)

    assert confidence == "suspeito"
    assert len(warnings) == 1
    assert "peso" in warnings[0]
    assert "903.0" in warnings[0]


def test_validate_nao_descarta_o_valor_fora_da_faixa() -> None:
    metrics = [Metric(key="imc", value=999, unit="kg/m2", ref_min=None, ref_max=None)]

    confidence, warnings = validate(_biometrics(), metrics)

    assert confidence == "suspeito"
    assert metrics[0].value == 999


def test_parse_leaf_valor_nao_numerico_lanca_formato_valor_invalido_error() -> None:
    with pytest.raises(FormatoValorInvalidoError) as exc_info:
        _parse_leaf("Erro!!", "peso")

    assert exc_info.value.campo == "peso"
    assert exc_info.value.valor_bruto == "Erro!!"


def test_parse_leaf_converte_numero_br_para_float() -> None:
    assert _parse_leaf("90,3", "peso") == 90.3


def test_parse_leaf_converte_numero_inteiro_sem_virgula() -> None:
    assert _parse_leaf("1883kcal", "taxa_metabolica_basal") == 1883


def test_parse_range_faixa_sem_separador_lanca_erro() -> None:
    with pytest.raises(FormatoValorInvalidoError):
        _parse_range("sem faixa aqui", "peso")
