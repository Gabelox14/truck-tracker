import pytest
from fastapi.testclient import TestClient

from app.api import intake as intake_api
from app.api.deps import require_staff_or_driver
from app.main import app
from app.schemas.intake import NhtsaDecodeOut
from app.services import nhtsa_service
from tests.helpers import FakeExtractor, make_extraction, make_jpeg


@pytest.fixture
def client():
    app.dependency_overrides[require_staff_or_driver] = lambda: "00000000-0000-0000-0000-000000000001"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def nhtsa(monkeypatch):
    """NHTSA simulado: responde según el VIN; registra las consultas."""
    responses: dict[str, NhtsaDecodeOut | None] = {}
    calls: list[str] = []

    def fake_decode(vin):
        calls.append(vin)
        return responses.get(vin, NhtsaDecodeOut(make="HONDA", model="Accord", model_year=2003, error_code="0"))

    monkeypatch.setattr(nhtsa_service, "decode_vin", fake_decode)
    return {"responses": responses, "calls": calls}


def _post(client, extractor, data=None, filename="vin.jpg", content_type="image/jpeg"):
    app.dependency_overrides[intake_api.get_extractor] = lambda: extractor
    return client.post(
        "/intake/vin-photo",
        files={"file": (filename, data if data is not None else make_jpeg(), content_type)},
    )


def test_valid_vin_is_ok(client, nhtsa):
    response = _post(client, FakeExtractor(make_extraction()))
    assert response.status_code == 200
    body = response.json()
    assert body["vin"] == "1HGCM82633A004352"
    assert body["vin_valid"] is True
    assert body["check_digit_ok"] is True
    assert body["nhtsa"]["make"] == "HONDA"
    assert body["nhtsa"]["model_year"] == 2003
    assert body["make_matches"] is True
    assert body["review_status"] == "ok"
    assert body["review_reasons"] == []
    assert body["usage"] == {"model": "claude-sonnet-5-5", "input_tokens": 1500, "output_tokens": 200, "calls": 1}


def test_x_check_digit_vin_is_ok(client, nhtsa):
    nhtsa["responses"]["1M8GDM9AXKP042788"] = NhtsaDecodeOut(make="MOTOR COACH INDUSTRIES", error_code="0")
    extraction = make_extraction(vin_text="1M8GDM9AXKP042788", make="Motor Coach Industries")
    body = _post(client, FakeExtractor(extraction)).json()
    assert body["check_digit_ok"] is True
    assert body["review_status"] == "ok"


def test_bad_check_digit_goes_to_review_but_is_kept(client, nhtsa):
    extractor = FakeExtractor(make_extraction(vin_text="1HGCM82633A004353"))
    body = _post(client, extractor).json()
    assert body["vin"] == "1HGCM82633A004353"
    assert body["vin_valid"] is True
    assert body["check_digit_ok"] is False
    assert body["review_status"] == "needs_review"
    assert any("dígito verificador" in reason for reason in body["review_reasons"])
    # Se intentó una segunda lectura con el recorte del VIN.
    assert [call["is_crop"] for call in extractor.calls] == [False, True]
    assert body["usage"]["calls"] == 2


def test_second_look_replaces_a_worse_reading(client, nhtsa):
    first = make_extraction(vin_text="1HGCM8?633A004352", confidence=0.4)
    closer = make_extraction(vin_text="1HGCM82633A004352", confidence=0.93, make=None, color=None)
    body = _post(client, FakeExtractor(first, closer), data=make_jpeg(4032, 3024)).json()
    assert body["vin"] == "1HGCM82633A004352"
    assert body["confidence"] == 0.93
    # La marca y el color se quedan con lo de la foto completa.
    assert body["make"] == "Honda"
    assert body["color"] == "gris"
    assert body["review_status"] == "ok"


def test_messy_reading_is_normalized(client, nhtsa):
    body = _post(client, FakeExtractor(make_extraction(vin_text="1hgcm82633a oo4352"))).json()
    assert body["vin_text"] == "1hgcm82633a oo4352"
    assert body["vin"] == "1HGCM82633A004352"
    assert body["check_digit_ok"] is True
    assert nhtsa["calls"] == ["1HGCM82633A004352"]


def test_no_vin_visible(client, nhtsa):
    extraction = make_extraction(vin_text=None, vin_location=None, vin_bbox=None, confidence=0)
    body = _post(client, FakeExtractor(extraction)).json()
    assert body["vin"] is None
    assert body["vin_valid"] is False
    assert body["review_status"] == "needs_review"
    assert "No se encontró un VIN en la foto" in body["review_reasons"]
    assert nhtsa["calls"] == []


def test_japanese_chassis_number_goes_to_review(client, nhtsa):
    extraction = make_extraction(vin_text="GRJ150-0012345", make="Toyota", vin_location="puerta")
    extractor = FakeExtractor(extraction)
    body = _post(client, extractor).json()
    assert body["vin_text"] == "GRJ150-0012345"
    assert body["vin"] == "GRJ1500012345"
    assert body["vin_valid"] is False
    assert body["review_status"] == "needs_review"
    assert nhtsa["calls"] == []
    # Lectura segura de un chasis: no hace falta segunda pasada.
    assert len(extractor.calls) == 1


def test_make_mismatch_goes_to_review(client, nhtsa):
    nhtsa["responses"]["1HGCM82633A004352"] = NhtsaDecodeOut(make="HONDA", error_code="0")
    body = _post(client, FakeExtractor(make_extraction(make="Toyota"))).json()
    assert body["make_matches"] is False
    assert body["review_status"] == "needs_review"
    assert any("no coincide" in reason for reason in body["review_reasons"])


def test_nhtsa_down_goes_to_review(client, nhtsa):
    nhtsa["responses"]["1HGCM82633A004352"] = None
    body = _post(client, FakeExtractor(make_extraction())).json()
    assert body["nhtsa"] is None
    assert body["review_status"] == "needs_review"
    assert "No se pudo consultar NHTSA para confirmar el VIN" in body["review_reasons"]


def test_rejects_non_image(client, nhtsa):
    response = _post(client, FakeExtractor(make_extraction()), data=b"%PDF-1.4", filename="x.pdf", content_type="application/pdf")
    assert response.status_code == 415


def test_rejects_empty_and_oversized_files(client, nhtsa, monkeypatch):
    assert _post(client, FakeExtractor(make_extraction()), data=b"").status_code == 400
    monkeypatch.setattr(intake_api.settings, "intake_max_image_mb", 0.01)
    response = _post(client, FakeExtractor(make_extraction()), data=make_jpeg(1600, 1200, color=(10, 120, 200)) + b"0" * 20000)
    assert response.status_code == 413


def test_without_api_key_answers_503(client):
    app.dependency_overrides.pop(intake_api.get_extractor, None)
    response = client.post("/intake/vin-photo", files={"file": ("vin.jpg", make_jpeg(), "image/jpeg")})
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_requires_authentication():
    app.dependency_overrides.clear()
    response = TestClient(app).post("/intake/vin-photo", files={"file": ("vin.jpg", make_jpeg(), "image/jpeg")})
    assert response.status_code in (401, 403)
