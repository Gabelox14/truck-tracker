"""Cuentas de chofer que crea el admin: el admin da el nombre y el sistema pone el
usuario y la contraseña, listos para entrar (sin registro ni correo de confirmación).
Por debajo cada cuenta es un usuario de Supabase Auth con email usuario@DRIVER_EMAIL_DOMAIN."""

import re
import secrets
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.driver import Driver
from app.models.profile import Profile
from app.models.trip import Trip
from app.services.auth_admin_service import AuthUserExists, SupabaseAuthAdmin
from app.services.text_utils import strip_accents

USERNAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,29}")

_CONSONANTS = "bcdfgjklmnprstvz"
_VOWELS = "aeiou"


class DriverAccountError(ValueError):
    pass


def email_for(username: str) -> str:
    return f"{username}@{settings.driver_email_domain}"


def username_for(email: str | None) -> str | None:
    """El usuario de una cuenta creada por el admin; None si se registró con su email."""
    suffix = f"@{settings.driver_email_domain}"
    if email and email.endswith(suffix):
        return email[: -len(suffix)]
    return None


def generate_password() -> str:
    """Fácil de dictar y de escribir en el celular: 'bodemi-4821'."""
    syllables = "".join(secrets.choice(_CONSONANTS) + secrets.choice(_VOWELS) for _ in range(3))
    return f"{syllables}-{secrets.randbelow(10000):04d}"


def username_candidates(full_name: str) -> list[str]:
    """'Carlos Pérez' → 'carlos', 'carlos.perez', 'carlos2', 'carlos3'…"""
    words = re.sub(r"[^a-z0-9]+", " ", strip_accents(full_name).lower()).split()
    if not words:
        raise DriverAccountError("El nombre necesita al menos una letra o número")
    first = words[0] if len(words[0]) >= 2 else "".join(words)[:28]
    candidates = [first]
    if len(words) > 1:
        candidates.append(f"{first}.{words[-1]}"[:30])
    candidates += [f"{first}{n}" for n in range(2, 100)]
    return [c for c in candidates if USERNAME_PATTERN.fullmatch(c)]


def attach_usernames(db: Session, drivers: list[Driver]) -> list[Driver]:
    ids = [d.profile_id for d in drivers]
    emails = dict(db.query(Profile.id, Profile.email).filter(Profile.id.in_(ids)).all()) if ids else {}
    for driver in drivers:
        driver.email = emails.get(driver.profile_id)
        driver.username = username_for(driver.email)
    return drivers


def create_account(db: Session, auth: SupabaseAuthAdmin, full_name: str, cedula: str | None = None) -> tuple[Driver, str]:
    full_name = " ".join(full_name.split())
    if not full_name:
        raise DriverAccountError("Falta el nombre del chofer")
    cedula = cedula.strip() if cedula and cedula.strip() else None
    if cedula and db.query(Profile.id).filter(Profile.cedula == cedula).first() is not None:
        raise DriverAccountError("Esa cédula ya está registrada")
    password = generate_password()

    taken = {email for (email,) in db.query(Profile.email).filter(Profile.email.like(f"%@{settings.driver_email_domain}"))}
    free = [u for u in username_candidates(full_name) if email_for(u) not in taken]
    # Supabase puede tener una cuenta con ese email que la base no conoce
    # (por ejemplo, una cuenta borrada a medias): se prueba el siguiente.
    for username in free[:5]:
        try:
            user_id = auth.create_user(email_for(username), password, full_name)
            break
        except AuthUserExists:
            continue
    else:
        raise DriverAccountError("No encontré un usuario libre para ese nombre")

    try:
        db.add(Profile(id=uuid.UUID(user_id), email=email_for(username), full_name=full_name, cedula=cedula, role="driver"))
        db.flush()
        driver = Driver(profile_id=uuid.UUID(user_id), full_name=full_name)
        db.add(driver)
        db.commit()
    except Exception:
        db.rollback()
        auth.delete_user(user_id)  # no dejar una cuenta que entra sin perfil
        raise
    db.refresh(driver)
    return attach_usernames(db, [driver])[0], password


def managed_profile(db: Session, driver: Driver) -> Profile | None:
    """El perfil si la cuenta la creó el admin; None si el chofer se registró solo."""
    profile = db.get(Profile, driver.profile_id)
    return profile if profile is not None and username_for(profile.email) is not None else None


def reset_password(db: Session, auth: SupabaseAuthAdmin, driver: Driver) -> str:
    profile = managed_profile(db, driver)
    if profile is None:
        raise DriverAccountError("Este chofer se registró con su propio email: su contraseña la maneja él")
    password = generate_password()
    auth.update_user(str(profile.id), password=password)
    return password


def set_login_enabled(db: Session, auth: SupabaseAuthAdmin, driver: Driver, enabled: bool) -> None:
    """Desactivar a un chofer de cuenta administrada también le cierra la entrada."""
    profile = managed_profile(db, driver)
    if profile is not None:
        auth.set_banned(str(profile.id), banned=not enabled)


def has_trips(db: Session, driver: Driver) -> bool:
    return db.query(Trip.id).filter(Trip.driver_id == driver.id).first() is not None


def delete_account(auth: SupabaseAuthAdmin, profile: Profile) -> None:
    """Borra la cuenta de Supabase; el perfil y el chofer caen en cascada."""
    auth.delete_user(str(profile.id))
