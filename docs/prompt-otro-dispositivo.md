Vas a preparar este equipo para trabajar en mi proyecto "Full Soluciones G&A S.A" (antes "Truck Tracker") y continuar el trabajo que dejé en otra computadora. Háblame en español, con avances cortos.

## Proyecto
- App interna de una empresa de grúas en Costa Rica: viajes, camiones, choferes, zonas, carros transportados (con VIN) y montos en colones o dólares.
- Repo: https://github.com/Gabelox14/truck-tracker. La rama master es producción: Render despliega el backend y Netlify el frontend automáticamente desde master.
- Backend en backend/: Python 3.12, FastAPI, SQLAlchemy y Alembic.
- Frontend en frontend/: React 19, Vite 8, Tailwind 3, TanStack Query y Axios.
- Datos y autenticación: Supabase (Postgres, Auth y Storage).

## 1. Instala lo necesario
Detecta el sistema operativo. Si es Windows, usa PowerShell y winget; si ya está instalado, solo confirma la versión.
- Git.
- Python 3.12 exactamente. No uses 3.13 ni 3.14: algunas dependencias fijadas no tienen paquetes compilados para esas versiones.
- Node.js LTS (24.x; Vite 8 necesita como mínimo 22.12).

En Windows:
- winget install --id Git.Git -e
- winget install --id Python.Python.3.12 -e
- winget install --id OpenJS.NodeJS.LTS -e

En macOS: brew install git python@3.12 node@24

## 2. Clona el repo
- En Windows, clónalo en C:\dev\truck-tracker, fuera de OneDrive. En la otra computadora, OneDrive dejó archivos "solo en la nube" y rompió git y node_modules.
- Cámbiate a la rama de trabajo: git checkout feature/ocr-intake

## 3. Backend
- Dentro de backend/, crea el entorno virtual con Python 3.12: "py -3.12 -m venv venv" en Windows o "python3.12 -m venv venv" en macOS.
- Instala las dependencias: venv\Scripts\python.exe -m pip install -r requirements-dev.txt (en macOS: venv/bin/python -m pip install -r requirements-dev.txt). Después corre pip check.
- Crea backend/.env copiando backend/.env.example.
- **No me pidas los valores secretos por el chat.** Dime qué variables faltan y yo las pego directo en el archivo.
- Variables:
  - SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY y DATABASE_URL. Salen del panel de Supabase: Project Settings → API, y Database → cadena de conexión del pooler.
  - CORS_ORIGINS=http://localhost:5173
  - ENVIRONMENT=development
  - Opcionales, para la captura automática: ANTHROPIC_API_KEY (Claude) y TRANSCRIPTION_API_KEY (Groq).
- Todas están documentadas en el README.

## 4. Frontend
- Dentro de frontend/, corre npm ci.
- Crea frontend/.env copiando frontend/.env.example, con:
  - VITE_API_URL=http://localhost:8000
  - VITE_SUPABASE_URL
  - VITE_SUPABASE_ANON_KEY (la llave anon, nunca la service_role).

## 5. Verifica
Repórtame el resultado en una tabla corta.
- Versiones de git, de Python dentro del venv, de node y de npm.
- pip check sin conflictos y npm ls sin errores.
- npm run build en frontend/.
- python -m pytest en backend/: deben pasar 71 y omitirse 30 (son las que necesitan TEST_DATABASE_URL).
- .claude/launch.json trae los servidores backend-dev (backend/dev.bat, con la ruta C:\dev\truck-tracker) y frontend-dev. Si la ruta o el sistema operativo son distintos, ajústalo para este equipo, pero no hagas commit de ese cambio.
- Levanta backend-dev y frontend-dev, y confirma que GET /health responde y que /login carga.

**Importante:**
- En la rama feature/ocr-intake el backend espera la migración b7c3e1f05a92, que todavía no está en la base de producción. Contra producción, los endpoints de viajes fallan hasta el merge; para usar la app real contra producción, corre master.
- Nunca apliques la migración de la rama a producción antes del merge. Render corre "alembic upgrade head" en cada arranque, así que el backend de master se caería.

## Estado del trabajo
En feature/ocr-intake están hechas y subidas las fases 1 a 5 de la captura automática (5 commits):
1. POST /intake/vin-photo: Claude lee el VIN de una foto; se valida con regex y dígito verificador y se decodifica con NHTSA vPIC.
2. Base de datos:
   - Tabla nueva intake_files.
   - trip_cars ampliada con VIN, modelo, año y revisión.
   - trips con moneda CRC o USD y estado de revisión.
   - Bucket privado intake-media.
3. POST /intake/audio: transcripción con Groq whisper-large-v3 (API compatible con OpenAI) y extracción con Claude de origen, destino, costo, moneda y vehículos.
4. Frontend:
   - Captura con cámara, galería o audio.
   - Página /viajes/:id.
   - Pestaña "Por revisar".
   - Moneda en montos y en el dashboard.
5. Excel FE ampliado: VIN, moneda, estado, enlace al viaje y hoja Resumen.

Después se probó con datos reales de "viajes directos" (fotos y notas de voz de WhatsApp contra el Excel que se llena a mano), y se agregó:
- Tarifas por ruta (pestaña "Tarifas" del admin), importadas del registro facturado. Los camiones JAC 1035/1042 pagan más que los livianos.
- Monto por vehículo; el total del viaje es la suma.
- Varias fotos por vehículo (etiqueta del VIN + carro) en una sola lectura.
- Del audio también se extraen la unidad (M2 → M02), el chofer, quién lo solicita, la factura directa y "más IVA".
- Excel "Formato Directos" idéntico al registro manual: con datos reales coincidieron 28 de 28 celdas.
- Pendiente: definir cómo se cobra "(REBOTE)" (el usuario dijo que "es Zapote"; en el registro se cobra la mitad de la ruta). Mientras tanto, los rebotes no se importan como tarifa.

Pendiente de mi parte:
- Poner ANTHROPIC_API_KEY y TRANSCRIPTION_API_KEY en backend/.env y en Render.
- Poner APP_BASE_URL y PYTHON_VERSION=3.12.10 en Render.
- Dar el OK para el merge a master.

Fase 6 (recibir fotos y audios directo desde WhatsApp Cloud API): no está empezada. Antes de arrancar, pregúntame si uso WhatsApp Business o el normal y espera mi OK.

## Cómo trabajo
- Español y avances muy cortos; dame detalle solo cuando algo falla o necesito decidir.
- En este repo, construye, verifica en el navegador, haz commit y push sin preguntarme en cada paso.
- Pregúntame antes de un merge a master, de una migración en producción, de un servicio pagado nuevo o de cualquier cosa destructiva.
- **Nunca dejes datos de prueba en producción:**
  - Crea usuarios desechables con la API Admin de Supabase y bórralos al terminar.
  - Confirma la limpieza con un SELECT.
  - No cambies el rol de mi cuenta real.
- Los secretos van solo en backend/.env y en Render; nunca en el frontend ni en variables VITE_ (la única excepción es la llave anon).
- Antes de tocar la interfaz, lee DESIGN.md y PRODUCT.md:
  - La paleta es casi monocroma: ámbar, esmeralda y rojo solo para estados.
  - El badge "Revisar" lleva borde de tinta.
  - Los montos siempre van con formatMoney(valor, moneda), y nunca se suman colones con dólares.
- Particularidades vistas en Windows:
  - La herramienta Bash convierte \\ en \ antes de ejecutar; escribe el código con escapes usando las herramientas de archivos, no con heredocs.
  - Los archivos del frontend usan finales de línea CRLF.
- Tests con base de datos:
  - Usa un Postgres local desechable; por ejemplo, pip install pgserver en otro venv, y luego initdb y pg_ctl con sus binarios.
  - Crea la tabla auth.users (id uuid primary key) y apunta TEST_DATABASE_URL a esa base.
  - Los tests se niegan a correr contra Supabase.

Empieza por los pasos 1 a 5 y repórtame el resultado.
