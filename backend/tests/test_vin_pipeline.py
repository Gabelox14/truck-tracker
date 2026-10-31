import pytest

from app.schemas.intake import NhtsaDecodeOut
from app.services import image_service, intake_service
from tests.helpers import FakeExtractor, make_extraction, make_jpeg

HONDA = NhtsaDecodeOut(make="HONDA", model="Accord", model_year=2003, error_code="0")


class FakeNhtsa:
    def __init__(self, responses=None, default=HONDA):
        self.responses = responses or {}
        self.default = default
        self.calls: list[str] = []

    def __call__(self, vin):
        self.calls.append(vin)
        return self.responses.get(vin, self.default)


def run(extractor, nhtsa=None, data=None):
    loaded = image_service.load(data if data is not None else make_jpeg())
    return intake_service.process_vin_photo(loaded, extractor, nhtsa or FakeNhtsa())


def test_valid_vin_is_ok():
    result = run(FakeExtractor(make_extraction()))
    assert result.vin == "1HGCM82633A004352"
    assert result.vin_valid is True
    assert result.check_digit_ok is True
    assert result.nhtsa.make == "HONDA"
    assert result.make_matches is True
    assert result.review_status == "ok"
    assert result.review_reasons == []
    assert result.usage.model_dump() == {"model": "claude-sonnet-5-5", "input_tokens": 1500, "output_tokens": 200, "calls": 1}


def test_x_check_digit_vin_is_ok():
    nhtsa = FakeNhtsa(default=NhtsaDecodeOut(make="MOTOR COACH INDUSTRIES", error_code="0"))
    result = run(FakeExtractor(make_extraction(vin_text="1M8GDM9AXKP042788", make="Motor Coach Industries")), nhtsa)
    assert result.check_digit_ok is True
    assert result.review_status == "ok"


def test_bad_check_digit_goes_to_review_but_is_kept():
    extractor = FakeExtractor(make_extraction(vin_text="1HGCM82633A004353"))
    result = run(extractor)
    assert result.vin == "1HGCM82633A004353"
    assert result.vin_valid is True
    assert result.check_digit_ok is False
    assert result.review_status == "needs_review"
    assert any("dígito verificador" in reason for reason in result.review_reasons)
    # Hubo una segunda lectura sobre el recorte del VIN.
    assert [call["is_crop"] for call in extractor.calls] == [False, True]
    assert result.usage.calls == 2


def test_second_look_replaces_a_worse_reading():
    first = make_extraction(vin_text="1HGCM8?633A004352", confidence=0.4)
    closer = make_extraction(vin_text="1HGCM82633A004352", confidence=0.93, make=None, color=None)
    result = run(FakeExtractor(first, closer), data=make_jpeg(4032, 3024))
    assert result.vin == "1HGCM82633A004352"
    assert result.confidence == 0.93
    # Marca y color se quedan con lo de la foto completa.
    assert result.make == "Honda"
    assert result.color == "gris"
    assert result.review_status == "ok"


def test_messy_reading_is_normalized():
    nhtsa = FakeNhtsa()
    result = run(FakeExtractor(make_extraction(vin_text="1hgcm82633a oo4352")), nhtsa)
    assert result.vin_text == "1hgcm82633a oo4352"
    assert result.vin == "1HGCM82633A004352"
    assert result.check_digit_ok is True
    assert nhtsa.calls == ["1HGCM82633A004352"]


def test_no_vin_visible():
    nhtsa = FakeNhtsa()
    extraction = make_extraction(vin_text=None, vin_location=None, vin_bbox=None, confidence=0)
    result = run(FakeExtractor(extraction), nhtsa)
    assert result.vin is None
    assert result.vin_valid is False
    assert result.review_status == "needs_review"
    assert "No se encontró un VIN en la foto" in result.review_reasons
    assert nhtsa.calls == []


def test_japanese_chassis_number_goes_to_review():
    nhtsa = FakeNhtsa()
    extractor = FakeExtractor(make_extraction(vin_text="GRJ150-0012345", make="Toyota", vin_location="puerta"))
    result = run(extractor, nhtsa)
    assert result.vin == "GRJ1500012345"
    assert result.vin_valid is False
    assert result.review_status == "needs_review"
    assert nhtsa.calls == []
    # Lectura segura de un chasis: no hace falta segunda pasada.
    assert len(extractor.calls) == 1


def test_make_mismatch_goes_to_review():
    result = run(FakeExtractor(make_extraction(make="Toyota")))
    assert result.make_matches is False
    assert result.review_status == "needs_review"
    assert any("no coincide" in reason for reason in result.review_reasons)


def test_nhtsa_down_goes_to_review():
    result = run(FakeExtractor(make_extraction()), FakeNhtsa(default=None))
    assert result.nhtsa is None
    assert result.review_status == "needs_review"
    assert "No se pudo consultar NHTSA para confirmar el VIN" in result.review_reasons


def test_low_confidence_and_bad_photo_are_flagged():
    result = run(FakeExtractor(make_extraction(confidence=0.5, image_quality="mala", vin_bbox=None)))
    assert result.review_status == "needs_review"
    assert any("poca seguridad" in reason for reason in result.review_reasons)
    assert "La foto es de mala calidad" in result.review_reasons


@pytest.mark.parametrize(
    ("check_digit_ok_vin", "nhtsa_make", "photo_make", "expected_brand"),
    [
        ("1HGCM82633A004352", "HONDA", "Honda", "Honda"),
        ("1HGCM82633A004352", "MERCEDES-BENZ", "Mercedes", "Mercedes-Benz"),
        ("1HGCM82633A004353", "HONDA", "Acura", "Acura"),
    ],
)
def test_car_fields_trust_nhtsa_only_with_valid_check_digit(check_digit_ok_vin, nhtsa_make, photo_make, expected_brand):
    nhtsa = FakeNhtsa(default=NhtsaDecodeOut(make=nhtsa_make, model="X", model_year=2020, error_code="0"))
    result = run(FakeExtractor(make_extraction(vin_text=check_digit_ok_vin, make=photo_make)), nhtsa)
    fields = intake_service.car_fields_from_vin_result(result)
    assert fields["brand"] == expected_brand
    assert fields["make_from_photo"] == photo_make
    assert fields["model_year"] == 2020
    assert fields["vin"] == check_digit_ok_vin
