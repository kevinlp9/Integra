"""
Punto de Entrada de la Aplicación
main.py: Inicializa FastAPI y configura todos los componentes
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import room_router
from app.core.database import engine
from app.models.room import Room
from app.models.activity import Activity

# Crear instancia de FastAPI
app = FastAPI(
    title="Salas API",
    description="API para gestión de salas de llamadas",
    version="1.0.0",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Crear tablas en la base de datos (solo desarrollo)
@app.on_event("startup")
async def startup():
    """Ejecuta al iniciar la aplicación"""
    async with engine.begin() as conn:
        await conn.run_sync(Room.metadata.create_all)
        await conn.run_sync(Activity.metadata.create_all)
    print("✅ Base de datos inicializada")


@app.on_event("shutdown")
async def shutdown():
    """Ejecuta al cerrar la aplicación"""
    await engine.dispose()
    print("✅ Conexión de base de datos cerrada")


# Registrar routers
app.include_router(room_router.router)


# Root endpoint
@app.get("/")
async def root():
    """Endpoint raíz para verificar que la API está funcionando"""
    return {
        "message": "Salas API - Ejecutándose correctamente",
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

