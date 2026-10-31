import os

# Antes de importar la app: los tests nunca deben tocar la base ni el Storage reales.
# Las variables de entorno tienen prioridad sobre backend/.env en pydantic-settings.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "postgresql://tests:tests@127.0.0.1:1/tests")
os.environ["SUPABASE_URL"] = "http://supabase.test"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["INTAKE_BUCKET"] = "intake-test"

import pytest  # noqa: E402

from app.services import nhtsa_service  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_nhtsa_cache():
    nhtsa_service.clear_cache()
    yield
    nhtsa_service.clear_cache()
