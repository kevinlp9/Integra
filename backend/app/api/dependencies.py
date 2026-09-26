"""
Capa API - Inyección de Dependencias
dependencies.py: Centraliza funciones de dependencias que se inyectan en los routers
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.security import verify_token


async def get_db_session() -> AsyncSession:
    """
    Dependencia para inyectar la sesión de base de datos en los routers.

    Uso en un router:
        @router.get("/rooms")
        async def get_rooms(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with get_session() as session:
        yield session


async def get_current_user(payload: dict = Depends(verify_token)) -> dict:
    """
    Dependencia para obtener el usuario autenticado desde el JWT token.

    Uso en un router:
        @router.get("/profile")
        async def get_profile(current_user: dict = Depends(get_current_user)):
            ...
    """
    return payload

