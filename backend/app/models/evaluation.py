"""
Capa Models - Modelos de Base de Datos
evaluation.py: Tabla transaccional con cada respuesta/voto individual emitido desde los teléfonos
"""
from sqlmodel import SQLModel, Field
from typing import Optional


class Evaluation(SQLModel, table=True):
    """Modelo de base de datos para una respuesta individual emitida por un participante"""

    __tablename__ = "evaluations"

    id: Optional[int] = Field(default=None, primary_key=True)
    exposition_id: int = Field(foreign_key="expositions.id")
    criteria_id: int = Field(foreign_key="rubric_criteria.id")
    evaluator_name: str  # Nombre completo del alumno/participante
    # Boleta del alumno evaluador (FK lógica -> alumnos.boleta). Vincula cada
    # evaluación con la cuenta autenticada que la emitió.
    evaluator_boleta: Optional[str] = Field(default=None, index=True)

    # Respuesta cruda dada por el participante: el número (rating), la opción
    # elegida (multiple_choice), "true"/"false" (true_false) o el texto libre.
    answer_value: Optional[str] = None

    # Puntaje resultante (0..max_score). None para preguntas abiertas que no
    # se autocalifican (open_text), simplemente se registra el texto.
    score_given: Optional[float] = None

    created_at: str




