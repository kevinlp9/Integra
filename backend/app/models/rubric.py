"""
Capa Models - Modelos de Base de Datos
rubric.py: Entidad SQLModel para Criterios de Evaluación (Rúbrica)
"""
from sqlmodel import SQLModel, Field
from typing import Optional


class Rubric(SQLModel, table=True):
    """Modelo de base de datos para Criterios de Evaluación de una Sala"""

    __tablename__ = "rubrics"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="rooms.id")
    criteria_name: str  # Ej: "Dominio del Tema", "Material Visual"
    description: Optional[str] = None
    max_score: float = Field(default=4.0)  # Puntuación máxima para este criterio
    order: int = Field(default=0)  # Orden de visualización
    created_at: str

