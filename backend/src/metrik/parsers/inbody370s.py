"""Parser do laudo de bioimpedância InBody370S (página 1 do PDF).

Estratégia (ver docs/specs/parser-inbody.md, "Estratégia de extração"): o
template deste aparelho desenha rótulos e molduras como imagem/vetor de
fundo — só os valores dinâmicos (números, ID, data) são texto extraível.
Por isso rótulo → valor é casado por **coordenada fixa**, calibrada a
partir dos 3 PDFs de exemplo em ``backend/tests/fixtures/inbody370s/``
(mesmo gerador, mesmo layout: os "top" de cada campo batem entre os três a
menos de 1pt; só o "x0" varia, quando o número é mais largo/estreito ou
posicionado proporcionalmente numa régua).

A exceção é "Sexo": o valor ("Masculino"/"Feminino") é desenhado como uma
pequena imagem rasterizada, não texto. Em vez de OCR (fora de escopo pelo
spec), comparamos um average-hash perceptual da região contra um hash de
referência conhecido — não é reconhecimento de caracteres livre, é uma
checagem de identidade contra um conjunto fechado de 2 imagens fixas do
template. Só temos amostra real de "Masculino" (as 3 fixtures são do mesmo
paciente); "Feminino" fica documentado como lacuna a preencher quando
houver uma amostra real.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pdfplumber
from PIL import Image

from .base import DeviceParser
from .errors import (
    FormatoValorInvalidoError,
    LayoutInesperadoError,
    PDFNaoTextualError,
)
from .models import Biometrics, Evaluation, EvaluationData, Metric, PatientRef, RawExtraction
from .validation import validate

PARSER_VERSION = "inbody370s-v1"
DEVICE_MODEL = "InBody370S"

# (top_min, top_max, x_min, x_max) calibrados nos 3 PDFs de exemplo (página 1)
_HEADER_REGIONS: dict[str, tuple[float, float, float, float]] = {
    "id": (64, 73, 0, 110),
    "altura": (64, 73, 110, 180),
    "idade": (64, 73, 180, 222),
    "data_hora": (64, 73, 260, 360),
}
_SEXO_BBOX: tuple[float, float, float, float] = (215, 64, 268, 82)

_METRIC_REGIONS: dict[str, tuple[float, float, float, float]] = {
    "peso": (165, 183, 300, 355),
    "imc": (403, 413, 85, 345),
    "pgc": (426, 437, 85, 345),
    "massa_muscular_esqueletica": (307, 319, 85, 345),
    "massa_gordura": (199, 218, 85, 140),
    "agua_corporal_total": (130, 148, 85, 140),
    "taxa_metabolica_basal": (576, 586, 450, 550),
    "gordura_visceral": (603, 613, 460, 536),
    "relacao_cintura_quadril": (589, 599, 450, 548),
    "pontuacao_inbody": (127, 135, 430, 462),
}

_METRIC_UNITS: dict[str, str | None] = {
    "peso": "kg",
    "imc": "kg/m2",
    "pgc": "%",
    "massa_muscular_esqueletica": "kg",
    "massa_gordura": "kg",
    "agua_corporal_total": "L",
    "taxa_metabolica_basal": "kcal",
    "gordura_visceral": "nivel",
    "relacao_cintura_quadril": None,
    "pontuacao_inbody": "pontos",
}

# métricas cujo template imprime uma faixa de referência "(min~max)" ao lado
_METRICS_COM_FAIXA = {
    "peso",
    "massa_gordura",
    "agua_corporal_total",
    "taxa_metabolica_basal",
    "gordura_visceral",
    "relacao_cintura_quadril",
}

_METRIC_ORDER = list(_METRIC_REGIONS.keys())

_NUM_RE = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d+|-?\d+,\d+|-?\d+")
_DATA_HORA_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})\.?$")

# average-hash (8x8, região _SEXO_BBOX, resolução 150dpi) da imagem
# "Masculino" desenhada pelo LookinBody120 5.0.0.1(004) — idêntico nas 3
# fixtures de exemplo. Sem amostra real de "Feminino" ainda disponível.
_SEXO_AHASH_MASCULINO = "1111111111111111100000111000000110000001111001111111111111111111"
_SEXO_AHASHES: dict[str, str] = {
    _SEXO_AHASH_MASCULINO: "M",
}


def _words_in_region(
    words: list[dict[str, Any]],
    region: tuple[float, float, float, float],
) -> list[dict[str, Any]]:
    top_min, top_max, x_min, x_max = region
    return [
        w
        for w in words
        if top_min <= w["top"] <= top_max and w["x1"] >= x_min and w["x0"] <= x_max
    ]


def _to_number(token: str) -> float | int:
    if "," in token:
        return float(token.replace(".", "").replace(",", "."))
    return int(token)


def _parse_leaf(raw: str, campo: str) -> float | int:
    match = _NUM_RE.match(raw.strip())
    if not match:
        raise FormatoValorInvalidoError(
            f"valor não numérico para o campo '{campo}': {raw!r}", campo, raw
        )
    try:
        return _to_number(match.group(0))
    except ValueError as exc:
        raise FormatoValorInvalidoError(
            f"valor não numérico para o campo '{campo}': {raw!r}", campo, raw
        ) from exc


def _parse_range(raw: str, campo: str) -> tuple[float | int, float | int]:
    cleaned = raw.strip().strip("()")
    partes = cleaned.split("~")
    if len(partes) != 2:
        raise FormatoValorInvalidoError(
            f"faixa de referência inválida para o campo '{campo}': {raw!r}", campo, raw
        )
    return _parse_leaf(partes[0], campo), _parse_leaf(partes[1], campo)


def _ahash(image: Image.Image, hash_size: int = 8) -> str:
    small = image.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
    pixels = list(small.tobytes())
    avg = sum(pixels) / len(pixels)
    return "".join("1" if p > avg else "0" for p in pixels)


def _hamming(a: str, b: str) -> int:
    return sum(c1 != c2 for c1, c2 in zip(a, b))


def _extrair_sexo(page: "pdfplumber.page.Page") -> str | None:
    crop = page.within_bbox(_SEXO_BBOX, relative=False, strict=False)
    image = crop.to_image(resolution=150).original
    hash_ = _ahash(image)
    for referencia, sexo in _SEXO_AHASHES.items():
        if _hamming(hash_, referencia) <= 6:
            return sexo
    return None


class InBody370SParser(DeviceParser):
    def parse(self, pdf_path: str | Path) -> EvaluationData:
        try:
            pdf = pdfplumber.open(pdf_path)
        except Exception as exc:  # arquivo corrompido/não é um PDF válido
            raise PDFNaoTextualError(
                f"não foi possível abrir o PDF (corrompido ou inválido): {exc}"
            ) from exc

        with pdf:
            if not pdf.pages:
                raise PDFNaoTextualError("PDF sem páginas")
            page = pdf.pages[0]
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            if not words:
                raise PDFNaoTextualError("PDF sem texto extraível (provável scan/imagem)")

            campos_faltantes: list[str] = []

            device_id = self._extrair_texto_simples(words, "id", campos_faltantes)
            altura_raw = self._extrair_texto_simples(words, "altura", campos_faltantes)
            idade_raw = self._extrair_texto_simples(words, "idade", campos_faltantes)
            data_hora = self._extrair_data_hora(words, campos_faltantes)
            sexo = _extrair_sexo(page)
            if sexo is None:
                campos_faltantes.append("sexo")

            metric_values, metric_ranges = self._extrair_metricas(words, campos_faltantes)

            if campos_faltantes:
                raise LayoutInesperadoError(
                    "Layout da página 1 não bate com o template do InBody370S. "
                    f"Campos não localizados: {', '.join(campos_faltantes)}",
                    campos_faltantes,
                )

        altura_cm = _parse_leaf(altura_raw, "altura")
        idade = _parse_leaf(idade_raw, "idade")

        evaluation = Evaluation(
            device_model=DEVICE_MODEL,
            measured_at=data_hora,
            patient_ref=PatientRef(device_id=device_id),
            biometrics=Biometrics(altura_cm=int(altura_cm), idade=int(idade), sexo=sexo),
        )

        metrics = [
            Metric(
                key=key,
                value=metric_values[key],
                unit=_METRIC_UNITS[key],
                ref_min=metric_ranges[key][0],
                ref_max=metric_ranges[key][1],
            )
            for key in _METRIC_ORDER
        ]

        confidence, warnings = validate(evaluation.biometrics, metrics)
        raw_extraction = RawExtraction(
            parser_version=PARSER_VERSION, confidence=confidence, warnings=warnings
        )

        return EvaluationData(evaluation=evaluation, metrics=metrics, raw_extraction=raw_extraction)

    @staticmethod
    def _extrair_texto_simples(
        words: list[dict[str, Any]], campo: str, campos_faltantes: list[str]
    ) -> str | None:
        achados = _words_in_region(words, _HEADER_REGIONS[campo])
        if not achados:
            campos_faltantes.append(campo)
            return None
        return achados[0]["text"]

    @staticmethod
    def _extrair_data_hora(
        words: list[dict[str, Any]], campos_faltantes: list[str]
    ) -> datetime | None:
        achados = sorted(
            _words_in_region(words, _HEADER_REGIONS["data_hora"]), key=lambda w: w["x0"]
        )
        if len(achados) < 2:
            campos_faltantes.append("data_hora")
            return None
        data_raw, hora_raw = achados[0]["text"], achados[1]["text"]
        match = _DATA_HORA_RE.match(data_raw)
        if not match or ":" not in hora_raw:
            raise FormatoValorInvalidoError(
                f"data/hora em formato inesperado: {data_raw!r} {hora_raw!r}",
                "data_hora",
                f"{data_raw} {hora_raw}",
            )
        dia, mes, ano = (int(g) for g in match.groups())
        hora_str, minuto_str = hora_raw.split(":", 1)
        try:
            return datetime(ano, mes, dia, int(hora_str), int(minuto_str))
        except ValueError as exc:
            raise FormatoValorInvalidoError(
                f"data/hora inválida: {data_raw!r} {hora_raw!r}",
                "data_hora",
                f"{data_raw} {hora_raw}",
            ) from exc

    @staticmethod
    def _extrair_metricas(
        words: list[dict[str, Any]], campos_faltantes: list[str]
    ) -> tuple[dict[str, float | int], dict[str, tuple[float | int | None, float | int | None]]]:
        valores: dict[str, float | int] = {}
        faixas: dict[str, tuple[float | int | None, float | int | None]] = {}

        for key in _METRIC_ORDER:
            achados = _words_in_region(words, _METRIC_REGIONS[key])
            if key in _METRICS_COM_FAIXA:
                valor_words = [w for w in achados if "~" not in w["text"]]
                faixa_words = [w for w in achados if "~" in w["text"]]
                if not valor_words or not faixa_words:
                    campos_faltantes.append(key)
                    continue
                valores[key] = _parse_leaf(valor_words[0]["text"], key)
                faixas[key] = _parse_range(faixa_words[0]["text"], key)
            else:
                if not achados:
                    campos_faltantes.append(key)
                    continue
                valores[key] = _parse_leaf(achados[0]["text"], key)
                faixas[key] = (None, None)

        return valores, faixas
