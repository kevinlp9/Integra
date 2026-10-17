"""
Capa Core - Base de Datos
database.py: Configuración del motor de SQLAlchemy y sesión asíncrona

Nota: cuando DATABASE_URL apunta al Connection Pooler de Supabase (Supavisor)
en modo "transaction" (puerto 6543), PgBouncer NO soporta prepared statements
reutilizables entre transacciones. Por eso se deshabilita el statement cache
de asyncpg (`statement_cache_size=0`); si usas la conexión directa (puerto
5432, IPv6) esto no afecta el funcionamiento, solo evita una micro-optimización.
"""
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

_USING_POOLER = ".pooler.supabase.com" in settings.DATABASE_URL

# Crear el motor asíncrono de SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to False en producción
    future=True,
    connect_args={"statement_cache_size": 0} if _USING_POOLER else {},
)

# Factory de sesiones asíncrona
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session():
    """Proporciona una sesión de base de datos como context manager async (`async with get_session() as session`)"""
    async with async_session_maker() as session:
        yield session

