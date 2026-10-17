"""
Capa Schemas - DTOs (Data Transfer Objects)
evaluation_dto.py: Clases Pydantic para la emisión de respuestas por parte de los participantes
"""
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AnswerSubmit(BaseModel):
    """
    Respuesta individual a una pregunta/criterio de la rúbrica. El campo que se
    debe llenar depende del `question_type` de la pregunta:
      - "rating": usar `score_given` (0..max_score)
      - "multiple_choice": usar `selected_option` (debe coincidir con una de las `options`)
      - "true_false": usar `selected_option` con "true" o "false"
      - "open_text": usar `text_answer` (respuesta libre, no autocalificable)
    """

    criteria_id: int
    score_given: Optional[float] = Field(default=None, ge=0)
    selected_option: Optional[str] = None
    text_answer: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one_answer(self) -> "AnswerSubmit":
        if self.score_given is None and self.selected_option is None and self.text_answer is None:
            raise ValueError(
                "Debes enviar 'score_given', 'selected_option' o 'text_answer' para cada respuesta"
            )
        return self


class EvaluationSubmit(BaseModel):
    """
    DTO recibido en POST /api/evaluations/submit.
    Contiene el arreglo de respuestas emitidas por un participante para el
    elemento (equipo/jugador/ronda) activo en la sala.

    Nota: la identidad del evaluador (boleta y nombre) se obtiene del token de
    alumno autenticado, no de este body. `evaluator_name` se conserva como
    opcional por compatibilidad, pero el backend lo ignora.
    """

    join_code: str = Field(..., min_length=1)
    evaluator_name: Optional[str] = Field(default=None, max_length=150)
    scores: list[AnswerSubmit] = Field(..., min_length=1)


