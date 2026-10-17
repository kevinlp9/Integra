"""
Capa API - Routes (Controladores)
auth_router.py: Endpoints de autenticación.

  - Profe (host): registro e inicio de sesión con correo + contraseña (JWT
    emitido por esta API). Además, sigue soportándose el login con Google vía
    Supabase en el frontend; este router valida ese JWT en /me.
  - Alumno: registro (boleta + correo + nombre + contraseña) e inicio de sesión
    con boleta + contraseña.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_teacher_id, get_current_user, get_db_session
from app.models.user import User
from app.schemas.auth_dto import (
    AlumnoLogin,
    AlumnoRegister,
    AlumnoTokenResponse,
    HostTokenResponse,
    ProfeLogin,
    ProfeRegister,
)
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


class MeResponse(BaseModel):
    id: UUID
    email: str | None = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Registro e inicio de sesión del profe (correo + contraseña)
# ---------------------------------------------------------------------------
@router.post("/register", response_model=HostTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_profe(
    payload: ProfeRegister,
    session: AsyncSession = Depends(get_db_session),
):
    """Registra un profe con correo y contraseña y devuelve un token de acceso."""
    return await AuthService(session).register_profe(payload)


@router.post("/login", response_model=HostTokenResponse)
async def login_profe(
    payload: ProfeLogin,
    session: AsyncSession = Depends(get_db_session),
):
    """Inicia sesión de un profe con correo y contraseña."""
    return await AuthService(session).login_profe(payload)


# ---------------------------------------------------------------------------
# Registro e inicio de sesión del alumno
#   - Registro: boleta + correo + nombre + contraseña
#   - Login: boleta + contraseña
# ---------------------------------------------------------------------------
@router.post("/alumno/register", response_model=AlumnoTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_alumno(
    payload: AlumnoRegister,
    session: AsyncSession = Depends(get_db_session),
):
    """Registra un alumno (boleta + correo + nombre + contraseña)."""
    return await AuthService(session).register_alumno(payload)


@router.post("/alumno/login", response_model=AlumnoTokenResponse)
async def login_alumno(
    payload: AlumnoLogin,
    session: AsyncSession = Depends(get_db_session),
):
    """Inicia sesión de un alumno con boleta y contraseña."""
    return await AuthService(session).login_alumno(payload)


@router.get("/me", response_model=MeResponse)
async def get_me(
    session: AsyncSession = Depends(get_db_session),
    payload: dict = Depends(get_current_user),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """
    Devuelve el perfil del profesor autenticado y sincroniza (upsert) su
    registro en la tabla `users`. Funciona tanto para profes de Google
    (Supabase) como para los registrados con correo/contraseña.
    """
    email = payload.get("email")

    stmt = select(User).where(User.id == teacher_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(id=teacher_id, email=email or f"{teacher_id}@unknown.local")
        session.add(user)
        await session.commit()
        await session.refresh(user)
    elif email and user.email != email:
        user.email = email
        await session.commit()
        await session.refresh(user)

    return user

