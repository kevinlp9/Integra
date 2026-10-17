"""
Capa Models - Modelos de Base de Datos
exposition.py: Entidad SQLModel para el elemento evaluable dentro de una Sala.

Genérico por diseño: puede representar un equipo que expone, un jugador,
un proyecto, una ronda de trivia, etc. Se evalúa uno a la vez (el que esté
activo en `room.current_exposition_id`), igual que las preguntas de un
Kahoot se muestran una por una.
"""
from typing import Optional

from sqlmodel import SQLModel, Field


class Exposition(SQLModel, table=True):
    """Modelo de base de datos para un elemento evaluable (equipo/jugador/ronda) de una Sala"""

    __tablename__ = "expositions"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="rooms.id")
    name: str  # Nombre del equipo, jugador, proyecto o ronda
    order: int = Field(default=0, index=True)  # Orden de presentación/turno
    final_score: Optional[float] = None  # Se calcula/congela al cerrar la evaluación
    created_at: str



