"""Modelos de dados do resultado de parsing, espelhando o schema do spec."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class PatientRef:
    device_id: str

    def to_dict(self) -> dict:
        return {"device_id": self.device_id}


@dataclass(frozen=True)
class Biometrics:
    altura_cm: int
    idade: int
    sexo: str

    def to_dict(self) -> dict:
        return {"altura_cm": self.altura_cm, "idade": self.idade, "sexo": self.sexo}


@dataclass(frozen=True)
class Evaluation:
    device_model: str
    measured_at: datetime
    patient_ref: PatientRef
    biometrics: Biometrics

    def to_dict(self) -> dict:
        return {
            "device_model": self.device_model,
            "measured_at": self.measured_at.isoformat(),
            "patient_ref": self.patient_ref.to_dict(),
            "biometrics": self.biometrics.to_dict(),
        }


@dataclass(frozen=True)
class Metric:
    key: str
    value: float | int
    unit: str | None
    ref_min: float | int | None
    ref_max: float | int | None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "ref_min": self.ref_min,
            "ref_max": self.ref_max,
        }


@dataclass(frozen=True)
class RawExtraction:
    parser_version: str
    confidence: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "parser_version": self.parser_version,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class EvaluationData:
    evaluation: Evaluation
    metrics: list[Metric]
    raw_extraction: RawExtraction

    def to_dict(self) -> dict:
        return {
            "evaluation": self.evaluation.to_dict(),
            "metrics": [m.to_dict() for m in self.metrics],
            "raw_extraction": self.raw_extraction.to_dict(),
        }
