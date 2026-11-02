import pytest

from app.services import rate_service
from app.services.text_utils import fold, short_name, unit_code


@pytest.mark.parametrize(
    ("name", "short"),
    [("David Sánchez", "DAVID S"), ("pablo fernández", "PABLO F"), ("Kennet", "KENNET"), ("", None), (None, None)],
)
def test_short_name_like_the_solicitado_column(name, short):
    assert short_name(name) == short


@pytest.mark.parametrize(
    ("said", "code"),
    [("M2", "M02"), ("m 2", "M02"), ("M-02", "M02"), ("M10", "M10"), ("JP", "JP"), ("myr", "MYR"), (None, None)],
)
def test_unit_code(said, code):
    assert unit_code(said) == code


def test_fold_ignores_accents_and_case():
    assert fold("Pérez  Zeledón") == fold("PEREZ ZELEDON") == "perez zeledon"


@pytest.mark.parametrize(
    ("make", "model", "vehicle_class"),
    [
        ("JAC", "1042", "carga"),
        ("JAC", "JAC 1035", "carga"),
        ("JAC", "T6", "liviano"),
        ("Suzuki", "Jimny", "liviano"),
        (None, None, "liviano"),
    ],
)
def test_vehicle_class_from_real_pricing(make, model, vehicle_class):
    assert rate_service.vehicle_class_for(make, model) == vehicle_class
