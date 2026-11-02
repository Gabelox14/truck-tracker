import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.drivers import router as drivers_router
from app.api.intake import router as intake_router
from app.api.profiles import router as profiles_router
from app.api.rates import router as rates_router
from app.api.trips import router as trips_router
from app.api.trucks import router as trucks_router
from app.api.zones import router as zones_router
from app.core.config import settings

# Logs propios (consumo de tokens, fallas de NHTSA) en la salida de Uvicorn/Render.
_app_logger = logging.getLogger("app")
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    _app_logger.addHandler(_handler)
    _app_logger.setLevel(logging.INFO)

app = FastAPI(title="Full Soluciones G&A S.A API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(profiles_router)
app.include_router(trucks_router)
app.include_router(drivers_router)
app.include_router(zones_router)
app.include_router(trips_router)
app.include_router(intake_router)
app.include_router(rates_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.environment}
