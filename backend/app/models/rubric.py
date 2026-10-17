"""
Capa Models - Modelos de Base de Datos
rubric.py: Entidad SQLModel para las preguntas/criterios de evaluación (rubric_criteria)

Genérico por diseño: una "pregunta" puede ser una calificación numérica
(rating, ej. rúbrica de exposición), una opción múltiple, un verdadero/falso
o una respuesta de texto libre. Así el mismo motor sirve tanto para evaluar
una exposición con rúbrica como para un cuestionario/trivia estilo Kahoot.
"""
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import SQLModel, Field

# Tipos de pregunta soportados
QUESTION_TYPE_RATING = "rating"                # Calificación numérica 0..max_score (rúbrica)
QUESTION_TYPE_MULTIPLE_CHOICE = "multiple_choice"  # Selección de una opción (autocalificable)
QUESTION_TYPE_TRUE_FALSE = "true_false"        # Verdadero/Falso (autocalificable)
QUESTION_TYPE_OPEN_TEXT = "open_text"          # Respuesta libre (no autocalificable)

VALID_QUESTION_TYPES = {
    QUESTION_TYPE_RATING,
    QUESTION_TYPE_MULTIPLE_CHOICE,
    QUESTION_TYPE_TRUE_FALSE,
    QUESTION_TYPE_OPEN_TEXT,
}


class RubricCriterion(SQLModel, table=True):
    """Modelo de base de datos para una pregunta/criterio de evaluación de una Sala"""

    __tablename__ = "rubric_criteria"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="rooms.id")
    name: str  # Enunciado. Ej: "Dominio del Tema", "¿Cuál es la capital de Perú?"
    question_type: str = Field(default=QUESTION_TYPE_RATING)
    max_score: float = Field(default=10.0)  # Puntaje máximo otorgable por esta pregunta

    # Solo aplica a multiple_choice: lista de opciones que verá el participante
    options: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))

    # Respuesta correcta para autocalificar multiple_choice/true_false.
    # NUNCA se debe exponer al participante (ver RubricCriterionPublic).
    correct_answer: Optional[str] = None



