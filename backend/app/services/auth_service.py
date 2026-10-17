"""
Capa Services - Lógica de Negocio
auth_service.py: Casos de uso de autenticación propia.

  - Profe (host): registro e inicio de sesión con correo + contraseña.
  - Alumno: registro con correo + contraseña + boleta; login con boleta + contraseña.

En ambos casos se emite un JWT firmado por esta API (ver core.security).
"""
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    ROLE_ALUMNO,
    ROLE_HOST,
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.alumno import Alumno
from app.models.user import User
from app.schemas.auth_dto import (
    AlumnoLogin,
    AlumnoRegister,
    AlumnoTokenResponse,
    HostTokenResponse,
    ProfeLogin,
    ProfeRegister,
)


class AuthService:
    """Servicio de negocio para el registro y autenticación propios."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ----------------------------- Profe / Host -----------------------------
    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def register_profe(self, data: ProfeRegister) -> HostTokenResponse:
        email = data.email.strip().lower()

        if await self._get_user_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta registrada con ese correo",
            )

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hash_password(data.password),
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return self._build_host_token(user)

    async def login_profe(self, data: ProfeLogin) -> HostTokenResponse:
        email = data.email.strip().lower()
        user = await self._get_user_by_email(email)

        if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Correo o contraseña incorrectos",
            )

        return self._build_host_token(user)

    def _build_host_token(self, user: User) -> HostTokenResponse:
        token = create_access_token(
            subject=str(user.id),
            role=ROLE_HOST,
            extra_claims={"email": user.email},
        )
        return HostTokenResponse(
            access_token=token,
            user={"id": str(user.id), "email": user.email},
        )

    # ------------------------------- Alumno ---------------------------------
    async def _get_alumno_by_boleta(self, boleta: str) -> Alumno | None:
        result = await self.session.execute(select(Alumno).where(Alumno.boleta == boleta))
        return result.scalar_one_or_none()

    async def _get_alumno_by_email(self, email: str) -> Alumno | None:
        result = await self.session.execute(select(Alumno).where(Alumno.email == email))
        return result.scalar_one_or_none()

    async def register_alumno(self, data: AlumnoRegister) -> AlumnoTokenResponse:
        boleta = data.boleta.strip()
        email = data.email.strip().lower()

        if await self._get_alumno_by_boleta(boleta):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta registrada con esa boleta",
            )
        if await self._get_alumno_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una cuenta registrada con ese correo",
            )

        alumno = Alumno(
            boleta=boleta,
            email=email,
            nombre=data.nombre.strip(),
            hashed_password=hash_password(data.password),
            created_at=datetime.utcnow().isoformat(),
        )
        self.session.add(alumno)
        await self.session.commit()
        await self.session.refresh(alumno)

        return self._build_alumno_token(alumno)

    async def login_alumno(self, data: AlumnoLogin) -> AlumnoTokenResponse:
        boleta = data.boleta.strip()
        alumno = await self._get_alumno_by_boleta(boleta)

        if not alumno or not verify_password(data.password, alumno.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Boleta o contraseña incorrectas",
            )

        return self._build_alumno_token(alumno)

    def _build_alumno_token(self, alumno: Alumno) -> AlumnoTokenResponse:
        token = create_access_token(
            subject=alumno.boleta,
            role=ROLE_ALUMNO,
            extra_claims={"email": alumno.email, "nombre": alumno.nombre},
        )
        return AlumnoTokenResponse(
            access_token=token,
            alumno={"boleta": alumno.boleta, "email": alumno.email, "nombre": alumno.nombre},
        )
