"""
Capa Models - Modelos de Base de Datos
room.py: Entidad SQLModel para la tabla de Salas.

Genérico: una Sala puede representar una clase con exposiciones de equipos,
un juego tipo Kahoot con rondas/preguntas, una sesión de votación, etc.
Cualquier "elemento evaluable" se modela como una Exposition (ronda/ítem).
"""
import uuid
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import SQLModel, Field


class Room(SQLModel, table=True):
    """Modelo de base de datos para una Sala de evaluación/juego interactivo"""

    __tablename__ = "rooms"

    id: Optional[int] = Field(default=None, primary_key=True)
    teacher_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), nullable=False),
    )  # FK lógica -> users.id (Supabase) - el "host" que controla la sala
    name: str = Field(index=True)  # Ej. "Cálculo Multivariable - 3BV2", "Trivia de Historia"
    join_code: str = Field(unique=True, index=True)  # Código para que los participantes se unan
    status: str = Field(default="waiting", index=True)  # waiting | active | finished
    current_exposition_id: Optional[int] = None  # Ítem/ronda actualmente activo
    created_at: str
    updated_at: Optional[str] = None




