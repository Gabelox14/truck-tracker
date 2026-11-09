import re
import unicodedata
from dataclasses import dataclass

VIN_LENGTH = 17
VIN_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

_TRANSLITERATION = {
    **{str(digit): digit for digit in range(10)},
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5,
    "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}
_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)

# Un VIN nunca lleva I, O ni Q: cuando aparecen en una lectura de 17 caracteres
# casi siempre son un 1 o un 0 mal leídos.
_LOOKALIKES = str.maketrans({"O": "0", "Q": "0", "I": "1"})

# Prefijo de fabricante (WMI, posiciones 1-3) → marca, para la flota que se
# transporta. NHTSA no conoce a estos fabricantes (son vehículos que no se venden
# en EE. UU.), así que la marca se confirma con esta tabla. Sale de los VIN reales
# del registro de viajes directos.
WMI_MAKES = {
    "MA3": "SUZUKI",  # Maruti Suzuki, India
    "MBH": "SUZUKI",  # Suzuki, India
    "MHY": "SUZUKI",  # Suzuki, Indonesia
    "JS1": "SUZUKI",
    "JS2": "SUZUKI",
    "JS3": "SUZUKI",
    "JS4": "SUZUKI",
    "LS4": "CHANGAN",
    "LS5": "CHANGAN",
    "LS6": "CHANGAN",
    "LSC": "CHANGAN",
    "LJ1": "JAC",
}

# Código de año (posición 10): se repite cada 30 años (A = 1980 y 2010, V = 1997 y 2027).
_YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"

_MAKE_ALIASES = {
    "VW": "VOLKSWAGEN",
    "CHEVY": "CHEVROLET",
    "MERCEDES": "MERCEDES BENZ",
    "BENZ": "MERCEDES BENZ",
    "RANGE ROVER": "LAND ROVER",
    # Marcas de Changan: sus VIN traen el prefijo de Changan (LS4/LS6).
    "DEEPAL": "CHANGAN",
    "AVATAR": "CHANGAN",
}


@dataclass(frozen=True)
class VinCheck:
    raw: str
    normalized: str
    is_valid: bool
    check_digit_ok: bool | None


def normalize(raw: str) -> str:
    """Mayúsculas y solo letras, números y '?' (marca de carácter ilegible).
    El cambio O/Q→0 e I→1 solo se aplica a lecturas de 17 caracteres, para no
    alterar números de chasis que no son VIN."""
    cleaned = re.sub(r"[^A-Z0-9?]", "", raw.upper())
    if len(cleaned) == VIN_LENGTH:
        cleaned = cleaned.translate(_LOOKALIKES)
    return cleaned


def compute_check_digit(vin: str) -> str:
    total = sum(_TRANSLITERATION[char] * weight for char, weight in zip(vin, _WEIGHTS))
    remainder = total % 11
    return "X" if remainder == 10 else str(remainder)


def analyze(raw: str) -> VinCheck:
    normalized = normalize(raw)
    is_valid = VIN_PATTERN.match(normalized) is not None
    check_digit_ok = normalized[8] == compute_check_digit(normalized) if is_valid else None
    return VinCheck(raw=raw, normalized=normalized, is_valid=is_valid, check_digit_ok=check_digit_ok)


def make_from_wmi(vin: str) -> str | None:
    return WMI_MAKES.get(vin[:3])


def vin_problem(vin: str | None, brand: str | None = None) -> str | None:
    """Por qué el VIN no sirve para facturar; None si está bien (o si no hay VIN).
    En el registro real de directos 195 de 196 VIN cumplen todo esto; el que no,
    era un error de digitación."""
    if not vin:
        return None
    check = analyze(vin)
    if "?" in check.normalized:
        return "El VIN tiene caracteres que no se pudieron leer"
    if not check.is_valid:
        if len(check.normalized) != VIN_LENGTH:
            return f"El VIN tiene {len(check.normalized)} caracteres; debe tener 17"
        return "El VIN tiene caracteres que no van en un VIN"
    if check.check_digit_ok is False:
        return "El dígito verificador no cuadra: revisa que el VIN esté bien escrito"
    vin_make = make_from_wmi(check.normalized)
    if brand and vin_make and not makes_match(brand, vin_make):
        return f"El VIN es de un {display_make(vin_make)}, pero el vehículo dice {brand}"
    return None


def latest_model_year(vin: str, current_year: int) -> int | None:
    """Año del VIN tomando el ciclo de 30 años más reciente que no pase del año
    siguiente: para carros nuevos, 'V' es 2027 y no 1997."""
    if len(vin) < 10 or vin[9] not in _YEAR_CODES:
        return None
    first = 1980 + _YEAR_CODES.index(vin[9])
    candidates = [first + 30 * cycle for cycle in range(3) if first + 30 * cycle <= current_year + 1]
    return max(candidates) if candidates else None


def normalize_make(make: str) -> str:
    without_accents = unicodedata.normalize("NFKD", make).encode("ascii", "ignore").decode()
    key = " ".join(re.sub(r"[^A-Z0-9]+", " ", without_accents.upper()).split())
    return _MAKE_ALIASES.get(key, key)


def makes_match(make_a: str, make_b: str) -> bool:
    """'MERCEDES-BENZ' = 'Mercedes', 'VW' = 'Volkswagen', 'TOYOTA' = 'Toyota'."""
    a, b = normalize_make(make_a), normalize_make(make_b)
    if not a or not b:
        return False
    shorter, longer = sorted((a, b), key=len)
    return longer == shorter or longer.startswith(shorter + " ")


def display_make(make: str) -> str:
    """'MERCEDES-BENZ' → 'Mercedes-Benz', 'LAND ROVER' → 'Land Rover', 'BMW' → 'BMW'."""

    def fix(word: str) -> str:
        return word if len(word) <= 3 and word.isupper() else word.capitalize()

    return " ".join("-".join(fix(part) for part in word.split("-")) for word in make.split())
