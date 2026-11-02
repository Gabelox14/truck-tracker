import pytest

from app.services import vin_service


def test_valid_vin():
    check = vin_service.analyze("1HGCM82633A004352")
    assert check.is_valid is True
    assert check.check_digit_ok is True
    assert check.normalized == "1HGCM82633A004352"


def test_valid_vin_with_x_check_digit():
    check = vin_service.analyze("1M8GDM9AXKP042788")
    assert vin_service.compute_check_digit("1M8GDM9AXKP042788") == "X"
    assert check.is_valid is True
    assert check.check_digit_ok is True


def test_invalid_check_digit_is_kept_not_discarded():
    check = vin_service.analyze("1HGCM82633A004353")
    assert check.is_valid is True
    assert check.check_digit_ok is False
    assert check.normalized == "1HGCM82633A004353"


def test_normalizes_case_spaces_and_lookalike_letters():
    check = vin_service.analyze("1hgcm82633a oo4352")
    assert check.normalized == "1HGCM82633A004352"
    assert check.is_valid is True
    assert check.check_digit_ok is True


def test_normalizes_hyphens_and_i_q():
    assert vin_service.normalize("1HGCM-8263-3AOO-435I") == "1HGCM82633A004351"
    assert vin_service.normalize("QHGCM82633A004352") == "0HGCM82633A004352"


def test_japanese_chassis_number_is_not_transliterated():
    check = vin_service.analyze("GRJ150-0012345")
    assert check.normalized == "GRJ1500012345"
    assert check.is_valid is False
    assert check.check_digit_ok is None


def test_unreadable_characters_are_kept_and_invalid():
    check = vin_service.analyze("1HGCM8?633A004352")
    assert check.normalized == "1HGCM8?633A004352"
    assert check.is_valid is False
    assert check.check_digit_ok is None


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("MERCEDES-BENZ", "Mercedes", True),
        ("Mercedes Benz", "MERCEDES-BENZ", True),
        ("VW", "VOLKSWAGEN", True),
        ("Chevy", "CHEVROLET", True),
        ("TOYOTA", "Toyota", True),
        ("Citroën", "CITROEN", True),
        ("HONDA", "Hyundai", False),
        ("Toyota", "LEXUS", False),
        ("KIA", "KIARA", False),
    ],
)
def test_makes_match(a, b, expected):
    assert vin_service.makes_match(a, b) is expected


@pytest.mark.parametrize(
    ("vin", "make"),
    [
        ("MBHWDB3S1VG905881", "SUZUKI"),
        ("MA3FL61SXTA573858", "SUZUKI"),
        ("JS3JB74V7V5105885", "SUZUKI"),
        ("MHYDN71VXVJ400814", "SUZUKI"),
        ("LS6CME0Z3VK910288", "CHANGAN"),
        ("LSCBBZ2GXVG802013", "CHANGAN"),
        ("LJ11PBBC1V1301733", "JAC"),
        ("1HGCM82633A004352", None),
    ],
)
def test_make_from_wmi_with_real_fleet_vins(vin, make):
    assert vin_service.make_from_wmi(vin) == make


@pytest.mark.parametrize(
    ("vin", "year"),
    [
        ("MBHWDB3S1VG905881", 2027),  # la etiqueta dice Año Modelo 2027; NHTSA diría 1997
        ("MA3FL61SXTA573858", 2026),
        ("MA3YPLCS3VK213370", 2027),
        ("1HGCM82633A004352", 2003),
    ],
)
def test_latest_model_year_picks_the_recent_cycle(vin, year):
    assert vin_service.latest_model_year(vin, 2026) == year


def test_display_make():
    assert vin_service.display_make("MERCEDES-BENZ") == "Mercedes-Benz"
    assert vin_service.display_make("LAND ROVER") == "Land Rover"
    assert vin_service.display_make("BMW") == "BMW"
    assert vin_service.display_make("TOYOTA") == "Toyota"
