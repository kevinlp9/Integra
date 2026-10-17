"""
Capa Schemas - DTOs (Data Transfer Objects)
room_dto.py: Clases Pydantic para validación de JSON de entrada/salida de Salas
"""
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from typing import Optional

from app.models.rubric import VALID_QUESTION_TYPES, QUESTION_TYPE_RATING, QUESTION_TYPE_MULTIPLE_CHOICE, \
    QUESTION_TYPE_TRUE_FALSE


class RoomCreate(BaseModel):
    """DTO para crear una nueva Sala - Datos que el profesor envía"""

    name: str = Field(..., min_length=1, max_length=100)


class RoomResponse(BaseModel):
    """DTO para la respuesta al cliente - Datos que serán enviados"""

    id: int
    teacher_id: UUID
    name: str
    join_code: str
    status: str
    current_exposition_id: Optional[int] = None
    created_at: str

    class Config:
        from_attributes = True  # Permite convertir modelos SQLModel a Pydantic


class RubricCriterionCreate(BaseModel):
    """
    DTO para agregar una pregunta/criterio de evaluación a una Sala.
    Soporta cualquier tipo de cuestionario o actividad:
      - "rating": calificación numérica 0..max_score (ej. rúbrica de exposición)
      - "multiple_choice": selección de una opción (autocalificable con `correct_answer`)
      - "true_false": verdadero/falso (autocalificable con `correct_answer`)
      - "open_text": respuesta libre (no autocalificable, solo se registra el texto)
    """

    name: str = Field(..., min_length=1, max_length=200)
    question_type: str = Field(default=QUESTION_TYPE_RATING)
    max_score: float = Field(default=10.0, gt=0)
    options: Optional[list[str]] = Field(default=None, description="Solo para multiple_choice")
    correct_answer: Optional[str] = Field(
        default=None, description="Solo para multiple_choice/true_false (autocalificación)"
    )

    @model_validator(mode="after")
    def _validate_by_type(self) -> "RubricCriterionCreate":
        if self.question_type not in VALID_QUESTION_TYPES:
            raise ValueError(
                f"question_type inválido. Debe ser uno de: {sorted(VALID_QUESTION_TYPES)}"
            )

        if self.question_type == QUESTION_TYPE_MULTIPLE_CHOICE:
            if not self.options or len(self.options) < 2:
                raise ValueError("multiple_choice requiere al menos 2 'options'")
            if self.correct_answer is None or self.correct_answer not in self.options:
                raise ValueError("correct_answer debe ser una de las 'options' proporcionadas")

        if self.question_type == QUESTION_TYPE_TRUE_FALSE:
            if self.correct_answer is None or self.correct_answer.lower() not in ("true", "false"):
                raise ValueError("correct_answer debe ser 'true' o 'false'")

        return self


class RubricCriterionResponse(BaseModel):
    """DTO de salida para el profesor: incluye la respuesta correcta"""

    id: int
    room_id: int
    name: str
    question_type: str
    max_score: float
    options: Optional[list[str]] = None
    correct_answer: Optional[str] = None

    class Config:
        from_attributes = True


class RubricCriterionPublic(BaseModel):
    """DTO de salida para los participantes: NUNCA incluye la respuesta correcta"""

    id: int
    room_id: int
    name: str
    question_type: str
    max_score: float
    options: Optional[list[str]] = None

    class Config:
        from_attributes = True


class ExpositionCreate(BaseModel):
    """DTO para registrar un elemento evaluable (equipo, jugador, proyecto, ronda) en la sala"""

    name: str = Field(..., min_length=1, max_length=100)
    order: Optional[int] = Field(default=None, ge=0)


class ExpositionResponse(BaseModel):
    """DTO de salida para un elemento evaluable de la sala"""

    id: int
    room_id: int
    name: str
    order: int
    final_score: Optional[float] = None

    class Config:
        from_attributes = True


class RoomJoinResponse(BaseModel):
    """DTO devuelto a los participantes al unirse con el join_code: estado actual de la sala"""

    room_id: int
    room_name: str
    room_status: str  # waiting | active | finished
    is_exposition_active: bool
    current_exposition: Optional[ExpositionResponse] = None
    rubric: list[RubricCriterionPublic] = []


class AlumnoRoomSummary(BaseModel):
    """DTO de salida para la lista 'Mis salas' del alumno (resumen por sala)."""

    room_id: int
    name: str
    join_code: str
    status: str  # waiting | active | finished

    class Config:
        from_attributes = True





