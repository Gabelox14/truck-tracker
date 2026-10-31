# Full Soluciones G&A S.A

Monorepo con frontend (React + Vite) y backend (FastAPI), sobre Supabase (Postgres + Auth).

## Estructura

```
truck-tracker/
├── frontend/   # React + Vite + Tailwind
├── backend/    # FastAPI + SQLAlchemy + Alembic
├── database/   # Migraciones
└── docs/
```

## Desarrollo

**Backend**

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # completar con credenciales de Supabase
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
cp .env.example .env   # completar con credenciales de Supabase
npm run dev
```

**Tests del backend** (sin llamadas reales: Claude, NHTSA y Storage van simulados)

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

## Variables de entorno del backend

Van en `backend/.env` y en Render; nunca en el frontend ni en variables `VITE_`.

| Variable | Obligatoria | Uso |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` | Sí | Supabase (Auth, Storage, Postgres) |
| `CORS_ORIGINS` | Sí en producción | Orígenes del frontend, separados por coma |
| `ANTHROPIC_API_KEY` | Para la captura | Llave de la API de Claude; sin ella `/intake` responde 503 |
| `ANTHROPIC_MODEL` | No (`claude-sonnet-5-5`) | Cambiar a `claude-haiku-5-5` para comparar costo |
| `ANTHROPIC_EFFORT` | No (`low`) | `low`, `medium`, `high`, `xhigh` o `max` |
| `INTAKE_MAX_IMAGE_MB` | No (`10`) | Tamaño máximo de foto aceptado |
