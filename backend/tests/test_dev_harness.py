from pathlib import Path

from fastapi.testclient import TestClient

from dev_harness.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "inbody370s"

client = TestClient(app)


def test_parse_pdf_real_retorna_200_com_json_extraido() -> None:
    with open(FIXTURES_DIR / "260827.pdf", "rb") as f:
        resp = client.post(
            "/dev/parse", files={"file": ("260827.pdf", f, "application/pdf")}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluation"]["device_model"] == "InBody370S"
    assert len(body["metrics"]) == 10


def test_parse_pdf_corrompido_retorna_422_com_erro_tipado() -> None:
    with open(FIXTURES_DIR / "corrupted.pdf", "rb") as f:
        resp = client.post(
            "/dev/parse", files={"file": ("corrupted.pdf", f, "application/pdf")}
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "PDFNaoTextualError"
    assert "message" in body


def test_parse_pdf_layout_inesperado_retorna_422() -> None:
    with open(FIXTURES_DIR / "layout_inesperado.pdf", "rb") as f:
        resp = client.post(
            "/dev/parse", files={"file": ("layout_inesperado.pdf", f, "application/pdf")}
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "LayoutInesperadoError"
