"""
Capa Models - Modelos de Base de Datos
user.py: Entidad SQLModel para la tabla de usuarios (profesores administrados por Supabase Auth)
"""
import uuid
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """Modelo de base de datos para un profesor (host)

    Puede autenticarse de dos formas:
      - Google (Supabase Auth): el `id` es el mismo UUID que genera Supabase y
        `hashed_password` queda en None.
      - Correo + contraseña (registro propio): se genera un UUID local y se
        almacena el hash de la contraseña en `hashed_password`.
    """

    __tablename__ = "users"

    id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )  # Mismo UUID que genera Supabase Auth, o uno local para login por contraseña
    email: str = Field(unique=True, index=True)
    # Hash bcrypt de la contraseña (None para profes que entran con Google)
    hashed_password: Optional[str] = Field(default=None)

