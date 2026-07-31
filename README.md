# Truck Tracker

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
