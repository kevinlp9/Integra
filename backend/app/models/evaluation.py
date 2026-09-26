"""
Capa Models - Modelos de Base de Datos
evaluation.py: Entidad SQLModel para Evaluaciones (Calificaciones granulares)
"""
from sqlmodel import SQLModel, Field
from typing import Optional


class Evaluation(SQLModel, table=True):
    """Modelo de base de datos para Evaluaciones por Criterio"""

    __tablename__ = "evaluations"

    id: Optional[int] = Field(default=None, primary_key=True)
    presentation_id: int = Field(foreign_key="presentations.id")
    rubric_id: int = Field(foreign_key="rubrics.id")
    evaluator_id: str  # ID del alumno en Supabase que está evaluando

    # La calificación
    score: float  # Puntuación otorgada (0 a max_score del criterio)
    comment: Optional[str] = None  # Comentario opcional del evaluador

    # Metadata
    created_at: str
    updated_at: Optional[str] = None

