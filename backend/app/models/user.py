"""
Capa Models - Modelos de Base de Datos
user.py: Entidad SQLModel para la tabla de usuarios (profesores administrados por Supabase Auth)
"""
import uuid

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """Modelo de base de datos para un profesor autenticado vía Supabase Auth"""

    __tablename__ = "users"

    id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )  # Mismo UUID que genera Supabase Auth
    email: str = Field(unique=True, index=True)

