# Backend de Evaluaciones Interactivas (estilo Kahoot)

API en FastAPI, genérica y reutilizable, para gestionar sesiones interactivas
en vivo: un **host** (profesor) crea una **sala** con un código de acceso,
define **preguntas/criterios** (rating, opción múltiple, verdadero/falso o
texto libre) y registra uno o más **elementos evaluables** (equipos,
jugadores, proyectos, rondas de trivia, etc.). Los **participantes**
(alumnos) se unen con el código —sin necesidad de cuenta— y responden sobre
el elemento que esté activo en cada momento, igual que en Kahoot se responde
una pregunta a la vez. Al finalizar, el host obtiene un **reporte con
ranking (leaderboard)**.

### Flujo general

1. El profesor (autenticado con **Supabase Auth**) crea una sala → recibe un `join_code`.
2. Define las preguntas/rúbrica (`rating`, `multiple_choice`, `true_false`, `open_text`) y registra los elementos a evaluar (equipos/rondas).
3. Los alumnos entran a la sala con el `join_code` (pantalla de espera, como el lobby de Kahoot).
4. El profesor pulsa **Iniciar** (`/start`): se activa el primer elemento.
5. Los alumnos responden sobre el elemento activo (`POST /api/evaluations/submit`).
6. El profesor pulsa **Siguiente** (`/next`) para avanzar; al llegar al último elemento, la sala se **finaliza** automáticamente y se congelan los puntajes.
7. El profesor consulta `GET /api/rooms/{id}/report` → ranking final ordenado por calificación.

## 📁 Estructura del Proyecto

```
/backend
├── .env                        # Credenciales (DATABASE_URL, SUPABASE_URL, API Keys)
├── requirements.txt
└── /app
    ├── main.py                 # Punto de entrada y lifespan
    ├── /core
    │   ├── config.py           # Carga de variables de entorno
    │   ├── database.py         # Motor de SQLAlchemy (ORM) y sesiones async
    │   └── security.py         # Validación del JWT de Supabase Auth (JWKS + legacy)
    ├── /models                 # Entidades de Base de Datos (SQLModel / ORM)
    │   ├── user.py             # Host/profesor (Supabase Auth)
    │   ├── room.py             # Sala: join_code, status (waiting/active/finished)
    │   ├── rubric.py           # RubricCriterion -> pregunta/criterio (rating/multiple_choice/true_false/open_text)
    │   ├── exposition.py       # Exposition -> elemento evaluable (equipo/jugador/ronda)
    │   └── evaluation.py       # Respuesta individual (answer_value + score_given)
    ├── /schemas                # DTOs Pydantic
    │   ├── room_dto.py
    │   ├── evaluation_dto.py
    │   └── report_dto.py
    ├── /api
    │   ├── dependencies.py     # DB Session, CurrentUser, CurrentTeacherId
    │   └── /routes
    │       ├── auth_router.py       # Perfil del host autenticado
    │       ├── room_router.py       # Salas, preguntas, elementos, control de sesión, reporte
    │       └── evaluation_router.py # Envío público de respuestas
    └── /services                # Lógica de Negocio
        ├── room_service.py          # Ciclo de vida de la sala (start/next/finish)
        ├── evaluation_service.py    # Validación y cálculo de respuestas por tipo de pregunta
        └── report_service.py        # Ranking (leaderboard) y congelado de puntajes
```

---

## 🏗️ Arquitectura en Capas (SOLID - Single Responsibility Principle)

### **Capa de Presentación** (`/api/routes`)
- Define los endpoints REST (GET, POST, PUT), valida datos con DTOs Pydantic
- Inyecta dependencias (sesión BD, `teacher_id` del host autenticado)
- NO contiene lógica de negocio

### **Capa de Negocio** (`/services`)
- `RoomService`: crea salas, genera `join_code`, gestiona preguntas/elementos y el ciclo de vida `waiting → active → finished`
- `EvaluationService`: resuelve y registra la respuesta según el tipo de pregunta (autocalifica `multiple_choice`/`true_false`, valida `rating`, guarda texto en `open_text`)
- `ReportService`: calcula promedios, arma el **ranking (leaderboard)** y congela los puntajes finales

### **Capa de Datos** (`/models`) — ORM SQLModel (SQLAlchemy + Pydantic)
- Mapea a las tablas `users`, `rooms`, `rubric_criteria`, `expositions`, `evaluations`

### **DTOs** (`/schemas`)
- Entrada: `RoomCreate`, `RubricCriterionCreate`, `ExpositionCreate`, `EvaluationSubmit`
- Salida: `RoomResponse`, `RoomJoinResponse` (rúbrica **sin** respuestas correctas), `RoomReport` (con ranking)

### **Inyección de Dependencias** (`/api/dependencies.py`)
- `get_db_session()`, `get_current_user()`, `get_current_teacher_id()`

### **Configuración** (`/core`)
- `config.py`: variables de entorno
- `database.py`: motor SQLAlchemy (ORM) y sesiones async (`asyncpg`)
- `security.py`: validación del JWT de Supabase Auth

---

## 🔐 Autenticación con Supabase Auth (JWKS + fallback legado)

Supabase migró de un secreto JWT compartido (HS256) a **llaves de firma
asimétricas** (ES256/RS256) publicadas en un endpoint JWKS público. Este
backend soporta **ambos esquemas automáticamente**:

1. **Nuevo esquema (recomendado, el que usa este proyecto):**
   `core/security.py` descarga y cachea en memoria las llaves públicas desde
   `${SUPABASE_URL}/auth/v1/.well-known/jwks.json`, identifica la llave por su
   `kid` (viene en el header del JWT) y verifica la firma (`ES256`) sin
   necesitar ningún secreto compartido. Si el `kid` no está en caché (rotación
   de llaves), se refresca automáticamente.
2. **Legado (opcional):** si defines `SUPABASE_JWT_SECRET` en el `.env` y el
   token viene firmado con `HS256`, se valida directamente con ese secreto
   (sin llamada de red).

**Host/Profesor (OAuth2 / JWT):**
1. Login en el frontend con "Continuar con Google" vía SDK de Supabase.
2. Supabase devuelve un JWT firmado (ES256 con las nuevas API Keys).
3. El frontend envía `Authorization: Bearer <TOKEN>` a FastAPI.
4. `core/security.py` valida el token (JWKS o secreto legado) y extrae el UUID (`sub`) del host para autorizar POST/PUT.

**Participantes/Alumnos (público controlado, sin cuenta):**
1. No requieren cuenta ni JWT.
2. Ingresan el `join_code` y su nombre completo.
3. `POST /api/evaluations/submit` valida que el `join_code` exista y la sala tenga un elemento **activo** antes de registrar las respuestas.

### 🔑 Nuevas API Keys de Supabase

Este proyecto usa el nuevo esquema de llaves del dashboard (**API Keys**):

| Variable | Uso | Dónde va |
|---|---|---|
| `SUPABASE_PUBLISHABLE_KEY` | Segura para exponer en el frontend/browser (requiere RLS) | Frontend + backend (opcional) |
| `SUPABASE_SECRET_KEY` | Acceso privilegiado, solo backend | Solo backend (`.env`, nunca en el frontend) |

> ℹ️ Estas API Keys **no** se usan para validar el JWT del usuario (eso lo
> hace el JWKS automáticamente); son para llamar directamente a la API REST
> o SDK de Supabase (Storage, RPC, Admin API, etc.) si lo necesitas.

---

---

## 🔒 Seguridad y manejo de secretos

**Regla de oro:** ningún secreto real (`DATABASE_URL` con contraseña,
`SUPABASE_SECRET_KEY`, `JWT_SECRET`, etc.) debe aparecer en código, `README`,
`FRONTEND_BRIEF.md`, commits de git ni archivos de configuración del IDE.
Solo viven en tu `.env` local (gitignorado) y en las *Environment Variables*
del panel de Render/hosting.

- `.env` y `.env.*` están en `.gitignore` (excepto `.env.example`, que solo
  tiene placeholders).
- `.idea/copilotDiffState.xml` (caché del asistente de IA en el IDE) también
  está en `.gitignore` — **verifica que no quede trackeado** con
  `git ls-files | grep copilotDiffState`; si aparece, hay que sacarlo del
  tracking (`git rm --cached .idea/copilotDiffState.xml`) porque puede
  contener el contenido completo de tu `.env` en texto plano.
- Antes de pegar logs, capturas o archivos en un chat/documento compartido,
  revisa que no incluyan JWTs, connection strings o API keys reales.

### Checklist de auditoría rápida (ejecútalo antes de cada push importante)
```bash
# Busca secretos reales que no deberían estar versionados
grep -rniE "sb_secret_|sb_publishable_[A-Za-z0-9_-]{15,}|postgresql\+asyncpg://[^<]" \
  --exclude-dir=.venv --exclude-dir=.git .

# Confirma qué archivos sensibles están trackeados por git
git ls-files | grep -E "\.env$|copilotDiffState"
```
Si algo aparece ahí y ya fue empujado a GitHub, **no basta con borrarlo del
commit actual** (el historial lo conserva). Hay que:
1. Quitarlo del tracking (`git rm --cached <archivo>`) y commitear.
2. **Rotar/regenerar esa credencial de inmediato** (Supabase Dashboard →
   API Keys / Database Password; y generar un nuevo `JWT_SECRET` con
   `python -c "import secrets; print(secrets.token_urlsafe(64))"`).
3. Actualizar `.env` local y las variables de entorno en Render con los
   valores nuevos.

---

## ☁️ Despliegue en Render

### Configuración del Web Service

| Campo | Valor |
|---|---|
| **Root Directory** | `backend` ⚠️ (el repo es un monorepo; `app/` vive dentro de `backend/`) |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT` |
| **Language** | Python 3 |

> ⚠️ El *Start Command* que Render sugiere por defecto
> (`gunicorn your_application.wsgi`) es para **Flask/Django (WSGI)**. FastAPI
> es **ASGI**, así que necesitas `gunicorn` con el *worker class* de
> `uvicorn` (ya agregado a `requirements.txt`). `$PORT` lo inyecta Render
> automáticamente, no lo definas tú.

La versión de Python queda fijada en `backend/runtime.txt` (`python-3.13.4`)
para evitar sorpresas si Render cambia su versión por defecto.

### Variables de entorno en Render

Copia los mismos valores de tu `.env` local, **más** `ALLOWED_ORIGINS`
apuntando al dominio real de tu frontend desplegado (no solo `localhost`):

| Key | Valor |
|---|---|
| `DATABASE_URL` | tu connection string del pooler (con la contraseña percent-encoded) |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_...` |
| `SUPABASE_SECRET_KEY` | `sb_secret_...` |
| `ALGORITHM` | `HS256` |
| `ALLOWED_ORIGINS` | `https://tu-frontend.vercel.app` (agrega `,http://localhost:3000` si quieres seguir probando en local contra el backend de Render) |
| `ALLOWED_ORIGIN_REGEX` | *(opcional)* `https://.*\.vercel\.app` si usas previews dinámicos |

### Notas del plan gratuito

- El plan **Free** "duerme" tras ~15 min de inactividad; la primera petición
  después de dormir tarda unos segundos (cold start) mientras arranca y
  vuelve a conectar con Supabase — es normal, no es un error.
- El pooler de Supabase (puerto `6543`) ya está optimizado para este tipo de
  conexiones cortas/frías, así que no necesitas cambiar `DATABASE_URL`.
- Una vez desplegado, verifica `https://<tu-servicio>.onrender.com/health`
  y `/docs` para confirmar que respondió `200`.

---

## 🌐 CORS

El middleware de CORS (`app/main.py`) **no usa `"*"`**. Solo permite los
orígenes exactos listados en `ALLOWED_ORIGINS` (.env, separados por coma):

```env
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Esto es obligatorio porque `allow_credentials=True` (necesario para enviar el
header `Authorization: Bearer <JWT>`): los navegadores **rechazan** la
combinación de `Access-Control-Allow-Origin: *` + credenciales, así que un
origen comodín simplemente no funcionaría desde el navegador.

- **Desarrollo local:** ya viene configurado para `localhost:3000`.
- **Producción:** agrega tu dominio real, ej. `https://mi-app.vercel.app`.
- **Previews dinámicos** (ej. cada deploy de Vercel tiene una URL distinta):
  usa `ALLOWED_ORIGIN_REGEX` en vez de listar cada uno:
  ```env
  ALLOWED_ORIGIN_REGEX=https://.*\.vercel\.app
  ```

Si el frontend recibe un error de CORS en la consola del navegador, casi
siempre es porque su origen (protocolo + dominio + puerto exactos) no está en
`ALLOWED_ORIGINS`. Agrégalo y reinicia el servidor.

## 🗄️ Conexión a la Base de Datos: Pooler vs. Directa (IPv6)

El hostname de conexión **directa** de Supabase (`db.<project-ref>.supabase.co`)
solo tiene registro **IPv6**. Muchas redes (hogar, algunos ISP, CI/CD) no
tienen salida IPv6 y fallan con `gaierror: nodename nor servname provided`.

**Solución:** usar el **Connection Pooler (Supavisor)**, que sí resuelve por
IPv4:

```
postgresql+asyncpg://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
```

- Usuario: `postgres.<project-ref>` (no solo `postgres`)
- Puerto `6543` = modo *transaction* (recomendado para backends con muchas conexiones cortas)
- Puerto `5432` = modo *session* (si necesitas `LISTEN/NOTIFY` o sesiones largas)
- La región (`<region>`, ej. `ca-central-1`) la encuentras en el Dashboard: **Project Settings > Database > Connection Pooling**.

> ⚠️ **Importante:** PgBouncer/Supavisor en modo *transaction* no soporta
> *prepared statements* reutilizables. Por eso `core/database.py` detecta
> automáticamente si `DATABASE_URL` usa el pooler y agrega
> `connect_args={"statement_cache_size": 0}` a `asyncpg`. Si cambias a la
> conexión directa (IPv6), este ajuste se omite automáticamente.

---

## 🕹️ Ciclo de vida de la Sala (estados estilo Kahoot)

```
waiting  --(POST /start)-->  active  --(PUT /next * N)-->  active  --(último item)-->  finished
   │                             │                                                         │
   └─ lobby: los participantes   └─ un elemento a la vez es evaluado                       └─ ranking congelado
      ya pueden unirse              (o salto manual con /activate/{exposition_id})            (GET /report)
```

## ❓ Tipos de Pregunta soportados (genérico)

| `question_type` | Campo de respuesta | Autocalificado | Uso típico |
|---|---|---|---|
| `rating` | `score_given` (0..max_score) | Sí (directo) | Rúbrica de exposición |
| `multiple_choice` | `selected_option` | Sí (compara con `correct_answer`) | Trivia/quiz |
| `true_false` | `selected_option` ("true"/"false") | Sí | Trivia/quiz |
| `open_text` | `text_answer` | No (solo se guarda el texto) | Encuestas/feedback |

---

## 🚀 Cómo Usar

### 1. Instalar dependencias
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configurar `.env`
```env
DATABASE_URL=postgresql+asyncpg://postgres:<PASSWORD>@db.<project-ref>.supabase.co:5432/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxxx
SUPABASE_SECRET_KEY=sb_secret_xxxxx
ALGORITHM=HS256
```

### 3. Ejecutar servidor
```bash
uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Docs interactivas: `http://localhost:8000/docs`

---

## 📝 Ejemplos de Uso (flujo completo)

### 1. Crear una sala (requiere JWT del host)
```bash
curl -X POST "http://localhost:8000/api/rooms" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Trivia de Historia"}'
```

### 2. Agregar preguntas (distintos tipos)
```bash
# Rating (rúbrica de exposición)
curl -X POST "http://localhost:8000/api/rooms/1/rubric" \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"name": "Dominio del Tema", "question_type": "rating", "max_score": 10}'

# Opción múltiple (autocalificada)
curl -X POST "http://localhost:8000/api/rooms/1/rubric" \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"name": "Capital de Perú", "question_type": "multiple_choice", "max_score": 5, "options": ["Lima","Cusco","Arequipa"], "correct_answer": "Lima"}'
```

### 3. Registrar elementos evaluables (equipos/jugadores/rondas)
```bash
curl -X POST "http://localhost:8000/api/rooms/1/expositions" \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"name": "Equipo A"}'
```

### 4. Iniciar la sesión (activa el primer elemento)
```bash
curl -X PUT "http://localhost:8000/api/rooms/1/start" -H "Authorization: Bearer <TOKEN>"
```

### 5. Unirse a la sala (alumno, público — lobby)
```bash
curl "http://localhost:8000/api/rooms/join/ROOM-9F3A"
```

### 6. Enviar respuestas (alumno, público)
```bash
curl -X POST "http://localhost:8000/api/evaluations/submit" \
  -H "Content-Type: application/json" \
  -d '{
        "join_code": "ROOM-9F3A",
        "evaluator_name": "Juan Pérez",
        "scores": [
          {"criteria_id": 1, "score_given": 9.5},
          {"criteria_id": 2, "selected_option": "Lima"}
        ]
      }'
```

### 7. Avanzar al siguiente elemento (o finalizar si era el último)
```bash
curl -X PUT "http://localhost:8000/api/rooms/1/next" -H "Authorization: Bearer <TOKEN>"
```

### 8. Obtener el reporte final (ranking / leaderboard)
```bash
curl "http://localhost:8000/api/rooms/1/report" -H "Authorization: Bearer <TOKEN>"
```

---

## ✨ Próximos Pasos

1. **Migrations** con Alembic (en lugar de `create_all` automático).
2. **Tests unitarios** para servicios.
3. **WebSockets** para actualizar el lobby/ranking en tiempo real sin polling.
4. **Rate limiting / anti-doble-voto** en `POST /api/evaluations/submit`.

