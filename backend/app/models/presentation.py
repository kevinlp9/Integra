"""
Capa Models - Modelos de Base de Datos
presentation.py: Entidad SQLModel para Exposiciones/Presentaciones de Equipos
"""
from sqlmodel import SQLModel, Field
from typing import Optional


class Presentation(SQLModel, table=True):
    """Modelo de base de datos para Exposiciones de Equipos"""

    __tablename__ = "presentations"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="rooms.id")
    team_name: str
    topic: Optional[str] = None  # Tema de la presentación
    order: int = Field(default=0)  # Orden de presentación

    # Campos para "congelar" el resultado
    final_score: Optional[float] = None  # Promedio final calculado
    teacher_feedback: Optional[str] = None  # Retroalimentación del profesor

    # Estados
    is_evaluated: bool = Field(default=False)  # Si ya fue evaluada
    evaluation_completed_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

