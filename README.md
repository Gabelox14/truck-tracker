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
| `APP_BASE_URL` | Recomendada en producción | URL pública del frontend para los enlaces del Excel (sin ella se usa el primer origen de `CORS_ORIGINS`) |
| `ANTHROPIC_API_KEY` | Para la captura | Llave de la API de Claude; sin ella `/intake` responde 503 |
| `ANTHROPIC_MODEL` | No (`claude-sonnet-5-5`) | Cambiar a `claude-haiku-5-5` para comparar costo |
| `ANTHROPIC_EFFORT` | No (`low`) | `low`, `medium`, `high`, `xhigh` o `max` |
| `TRANSCRIPTION_API_KEY` | Para notas de voz | Llave de la API de transcripción; sin ella `/intake/audio` responde 503 |
| `TRANSCRIPTION_BASE_URL` | No (`https://api.groq.com/openai/v1`) | Cualquier API compatible con OpenAI; para OpenAI: `https://api.openai.com/v1` |
| `TRANSCRIPTION_MODEL` | No (`whisper-large-v3`) | En OpenAI: `gpt-4o-transcribe` o `gpt-4o-mini-transcribe` |
| `INTAKE_MAX_IMAGE_MB` | No (`10`) | Tamaño máximo de foto aceptado |
| `INTAKE_MAX_AUDIO_MB` | No (`25`) | Tamaño máximo de nota de voz (Groq gratis acepta hasta 25 MB) |
| `INTAKE_BUCKET` | No (`intake-media`) | Bucket privado de fotos y audios (lo crea la migración) |

Las pruebas que usan base de datos corren solo si `TEST_DATABASE_URL` apunta a un Postgres
local desechable (nunca a Supabase; el test se niega a correr si detecta Supabase):

```bash
$env:TEST_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/tt_test"
python -m pytest
```
