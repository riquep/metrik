"""Interface comum a parsers de laudos de bioimpedância.

Trocar de aparelho/fabricante deve significar implementar uma nova
subclasse de :class:`DeviceParser`, sem reescrever o pipeline que a chama.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .models import EvaluationData


class DeviceParser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str | Path) -> EvaluationData:
        """Extrai os dados da avaliação a partir de um PDF de laudo.

        Deve lançar ``PDFNaoTextualError``, ``LayoutInesperadoError`` ou
        ``FormatoValorInvalidoError`` (ver ``errors.py``) em vez de
        exceções genéricas.
        """
        raise NotImplementedError
