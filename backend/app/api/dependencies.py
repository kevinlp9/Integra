"""
Capa API - Inyección de Dependencias
dependencies.py: Centraliza funciones de dependencias que se inyectan en los routers
(DB Session, CurrentUser)
"""
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.security import verify_token, get_teacher_id_from_payload, get_boleta_from_payload


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
    Dependencia para obtener el payload del usuario autenticado desde el JWT de Supabase.

    Uso en un router:
        @router.get("/profile")
        async def get_profile(current_user: dict = Depends(get_current_user)):
            ...
    """
    return payload


async def get_current_teacher_id(payload: dict = Depends(verify_token)) -> UUID:
    """
    Dependencia que extrae el UUID del profesor autenticado desde el JWT de Supabase.
    Se usa para autorizar operaciones de creación/actualización (POST, PUT, DELETE).

    Uso en un router:
        @router.post("/rooms")
        async def create_room(teacher_id: UUID = Depends(get_current_teacher_id)):
            ...
    """
    return get_teacher_id_from_payload(payload)


async def get_current_alumno(payload: dict = Depends(verify_token)) -> dict:
    """
    Dependencia que valida un token de alumno y devuelve su identidad
    ({"boleta", "nombre", "email"}). Se usa para autorizar la emisión de
    evaluaciones (el alumno debe iniciar sesión con boleta + contraseña).

    Uso en un router:
        @router.post("/evaluations/submit")
        async def submit(alumno: dict = Depends(get_current_alumno)):
            ...
    """
    boleta = get_boleta_from_payload(payload)
    return {
        "boleta": boleta,
        "nombre": payload.get("nombre") or boleta,
        "email": payload.get("email"),
    }



