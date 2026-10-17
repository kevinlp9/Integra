"""
Punto de Entrada de la Aplicación
main.py: Inicializa FastAPI y configura el ciclo de vida (lifespan) de todos los componentes
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth_router, evaluation_router, room_router
from app.core.config import settings
from app.core.database import engine
from app.core.migrations import run_startup_migrations
from app.models.evaluation import Evaluation
from app.models.exposition import Exposition
from app.models.room import Room
from app.models.rubric import RubricCriterion
from app.models.user import User
from app.models.alumno import Alumno
from app.models.alumno_sala import AlumnoSala


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación (startup/shutdown)"""
    # Startup: crear tablas que no existan (ej. `alumnos`) y aplicar migraciones
    # idempotentes de columnas sobre tablas ya existentes (`users`, `evaluations`).
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all)
        await run_startup_migrations(conn)
    print("✅ Base de datos inicializada")

    yield

    # Shutdown
    await engine.dispose()
    print("✅ Conexión de base de datos cerrada")


# Crear instancia de FastAPI
app = FastAPI(
    title="Backend de Evaluaciones Interactivas",
    description="API para gestión de salas de evaluación interactiva en tiempo real",
    version="1.0.0",
    lifespan=lifespan,
)

# Configurar CORS
# Solo se permiten los orígenes explícitos definidos en ALLOWED_ORIGINS (.env),
# nunca "*", porque allow_credentials=True requiere Bearer/cookies desde
# orígenes conocidos (el navegador rechazaría "*" + credenciales de todos modos).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registrar routers
app.include_router(auth_router.router)
app.include_router(room_router.router)
app.include_router(evaluation_router.router)


# Root endpoint
@app.get("/")
async def root():
    """Endpoint raíz para verificar que la API está funcionando"""
    return {
        "message": "Backend de Evaluaciones Interactivas - Ejecutándose correctamente",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



