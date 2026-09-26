"""
Capa Core - Base de Datos
database.py: Configuración del motor de SQLAlchemy y sesión asíncrona
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings


# Crear el motor asíncrono de SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to False en producción
    future=True,
)

# Factory de sesiones asíncrona
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    """Proporciona una sesión de base de datos"""
    async with async_session_maker() as session:
        yield session

