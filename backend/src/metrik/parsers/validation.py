"""Validação de plausibilidade fisiológica (ver spec, seção "Validação").

Nenhuma métrica é descartada por falhar aqui: o valor é sempre incluído no
resultado, e a falha apenas rebaixa ``confidence`` para ``"suspeito"`` e
acrescenta um warning legível.
"""

from __future__ import annotations

from .models import Biometrics, Metric

# chave canônica -> (mínimo plausível, máximo plausível)
PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "peso": (20, 300),
    "altura_cm": (100, 250),
    "pgc": (3, 70),
    "imc": (10, 80),
}


def validate(biometrics: Biometrics, metrics: list[Metric]) -> tuple[str, list[str]]:
    warnings: list[str] = []

    altura_min, altura_max = PLAUSIBLE_RANGES["altura_cm"]
    if not (altura_min <= biometrics.altura_cm <= altura_max):
        warnings.append(
            f"altura_cm fora da faixa plausível: {biometrics.altura_cm} cm — "
            "possível erro de parsing de vírgula/ponto"
        )

    for metric in metrics:
        faixa = PLAUSIBLE_RANGES.get(metric.key)
        if faixa is None:
            continue
        minimo, maximo = faixa
        if not (minimo <= metric.value <= maximo):
            warnings.append(
                f"{metric.key} fora da faixa plausível: {metric.value} "
                f"{metric.unit or ''} — possível erro de parsing de vírgula/ponto".rstrip()
            )

    confidence = "suspeito" if warnings else "ok"
    return confidence, warnings
