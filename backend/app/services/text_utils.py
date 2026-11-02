import re
import unicodedata


def strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def fold(text: str) -> str:
    """Minúsculas, sin tildes ni signos: para comparar nombres de lugares y personas."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", strip_accents(text).lower()).split())


def short_name(full_name: str | None) -> str | None:
    """'David Sánchez' → 'DAVID S', como en la columna SOLICITADO del registro de directos."""
    if not full_name:
        return None
    parts = strip_accents(full_name).upper().split()
    if not parts:
        return None
    return f"{parts[0]} {parts[1][0]}" if len(parts) > 1 else parts[0]


def unit_code(text: str | None) -> str | None:
    """'M2', 'm 2', 'M-02' → 'M02'; códigos sin número ('JP', 'MYR') quedan en mayúscula."""
    if not text:
        return None
    compact = re.sub(r"[^A-Z0-9]", "", strip_accents(text).upper())
    match = re.fullmatch(r"([A-Z]+)0*(\d+)", compact)
    if match:
        return f"{match.group(1)}{int(match.group(2)):02d}"
    return compact or None
