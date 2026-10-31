import os
from pathlib import Path

# Antes de importar la app: los tests nunca deben tocar la base ni el Storage reales.
# Las variables de entorno tienen prioridad sobre backend/.env en pydantic-settings.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "postgresql://tests:tests@127.0.0.1:1/tests"
os.environ["SUPABASE_URL"] = "http://supabase.test"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["INTAKE_BUCKET"] = "intake-test"

import pytest  # noqa: E402

from app.services import nhtsa_service  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def pytest_configure(config):
    if TEST_DATABASE_URL and "supabase" in TEST_DATABASE_URL:
        pytest.exit("TEST_DATABASE_URL apunta a Supabase: usa una base local desechable", returncode=2)


@pytest.fixture(autouse=True)
def _clear_nhtsa_cache():
    nhtsa_service.clear_cache()
    yield
    nhtsa_service.clear_cache()


@pytest.fixture(scope="session")
def migrated_engine():
    """Base local desechable con todas las migraciones aplicadas (TEST_DATABASE_URL)."""
    if not TEST_DATABASE_URL:
        pytest.skip("Sin TEST_DATABASE_URL se omiten las pruebas con base de datos")
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        # Supabase trae auth.users; en un Postgres común se simula para la FK de profiles.
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS auth.users (id uuid PRIMARY KEY, email text)"))
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(migrated_engine):
    """Sesión dentro de una transacción que se revierte al terminar cada test."""
    from sqlalchemy.orm import Session

    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
