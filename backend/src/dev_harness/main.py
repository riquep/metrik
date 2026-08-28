"""Harness de teste manual — upload de PDF + extração (ver docs/specs/harness-teste-parser.md).

⚠️ Descartável: ferramenta de desenvolvimento, sem autenticação, sem
persistência. Deve ser removida (ou movida para /dev-tools) quando a etapa
de fundação (auth + multi-tenancy + modelo de dados) existir.
"""

from __future__ import annotations

import io

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from metrik.parsers.errors import (
    FormatoValorInvalidoError,
    LayoutInesperadoError,
    PDFNaoTextualError,
)
from metrik.parsers.inbody370s import InBody370SParser

app = FastAPI(title="InBody370S dev harness (descartável)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_parser = InBody370SParser()


@app.post("/dev/parse")
async def parse_pdf(file: UploadFile = File(...)) -> dict:
    conteudo = await file.read()
    try:
        resultado = _parser.parse(io.BytesIO(conteudo))
    except (PDFNaoTextualError, LayoutInesperadoError, FormatoValorInvalidoError) as exc:
        return JSONResponse(
            status_code=422,
            content={"error": type(exc).__name__, "message": str(exc)},
        )
    return resultado.to_dict()
