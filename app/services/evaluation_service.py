"""
Capa Services - Lógica de Negocio
evaluation_service.py: Casos de uso para la emisión de respuestas por parte de los participantes.

Soporta cualquier tipo de pregunta/actividad (genérico, estilo Kahoot):
  - rating: calificación numérica directa (ej. rúbrica de exposición)
  - multiple_choice / true_false: autocalificadas comparando contra `correct_answer`
  - open_text: respuesta libre, no autocalificable (score_given queda en None)
"""
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.exposition import Exposition
from app.models.room import Room
from app.models.alumno_sala import AlumnoSala
from app.models.rubric import (
    RubricCriterion,
    QUESTION_TYPE_RATING,
    QUESTION_TYPE_MULTIPLE_CHOICE,
    QUESTION_TYPE_TRUE_FALSE,
    QUESTION_TYPE_OPEN_TEXT,
)
from app.schemas.evaluation_dto import AnswerSubmit, EvaluationSubmit


class EvaluationService:
    """Servicio de negocio para la emisión de respuestas de los participantes"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _resolve_answer(self, criterion: RubricCriterion, entry: AnswerSubmit) -> tuple[str, float | None]:
        """
        Calcula (answer_value, score_given) según el tipo de pregunta del criterio.
        Lanza HTTPException 400 si la respuesta no es válida para ese tipo.
        """
        if criterion.question_type == QUESTION_TYPE_RATING:
            if entry.score_given is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La pregunta '{criterion.name}' requiere 'score_given'",
                )
            if entry.score_given > criterion.max_score:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'score_given' no puede superar max_score ({criterion.max_score}) en '{criterion.name}'",
                )
            return str(entry.score_given), float(entry.score_given)

        if criterion.question_type in (QUESTION_TYPE_MULTIPLE_CHOICE, QUESTION_TYPE_TRUE_FALSE):
            if not entry.selected_option:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La pregunta '{criterion.name}' requiere 'selected_option'",
                )

            if criterion.question_type == QUESTION_TYPE_MULTIPLE_CHOICE:
                if criterion.options and entry.selected_option not in criterion.options:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"'selected_option' inválida para la pregunta '{criterion.name}'",
                    )
                is_correct = entry.selected_option == criterion.correct_answer
            else:  # true_false
                normalized = entry.selected_option.strip().lower()
                if normalized not in ("true", "false"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"'selected_option' debe ser 'true' o 'false' en '{criterion.name}'",
                    )
                is_correct = normalized == (criterion.correct_answer or "").strip().lower()

            score = criterion.max_score if is_correct else 0.0
            return entry.selected_option, score

        if criterion.question_type == QUESTION_TYPE_OPEN_TEXT:
            if not entry.text_answer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La pregunta '{criterion.name}' requiere 'text_answer'",
                )
            # Respuesta libre: no se autocalifica, solo se registra el texto.
            return entry.text_answer, None

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de pregunta no soportado: {criterion.question_type}",
        )

    async def submit_evaluation(self, data: EvaluationSubmit, alumno: dict) -> list[Evaluation]:
        """
        Valida que el join_code exista, que la sala tenga un elemento activo,
        y registra las respuestas vinculadas al alumno autenticado (boleta y
        nombre tomados del token, no del body).
        """
        # 1. Validar que la sala exista mediante el join_code
        stmt = select(Room).where(Room.join_code == data.join_code)
        result = await self.session.execute(stmt)
        room = result.scalar_one_or_none()

        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código de sala inválido",
            )

        # 1b. Validar que el alumno esté inscrito en la sala (se unió con el código)
        stmt = select(AlumnoSala.id).where(
            AlumnoSala.room_id == room.id,
            AlumnoSala.boleta == alumno["boleta"],
        )
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No estás inscrito en esta sala. Únete primero con el código.",
            )

        # 2. Validar que la sala tenga un elemento evaluable activo actualmente
        if room.status != "active" or not room.current_exposition_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sala no tiene ningún elemento activo para evaluar en este momento",
            )

        # 3. Validar que el elemento activo siga perteneciendo a la sala
        stmt = select(Exposition).where(Exposition.id == room.current_exposition_id)
        result = await self.session.execute(stmt)
        exposition = result.scalar_one_or_none()

        if not exposition or exposition.room_id != room.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El elemento activo ya no es válido para esta sala",
            )

        # 4. Obtener y validar que todos los criterios/preguntas enviados pertenezcan a la sala
        criteria_ids = [entry.criteria_id for entry in data.scores]
        stmt = select(RubricCriterion).where(
            RubricCriterion.id.in_(criteria_ids),
            RubricCriterion.room_id == room.id,
        )
        result = await self.session.execute(stmt)
        criteria_by_id = {c.id: c for c in result.scalars().all()}

        if set(criteria_ids) - set(criteria_by_id.keys()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Una o más preguntas no pertenecen a esta sala",
            )

        # 5. Resolver y registrar cada respuesta individual según su tipo de pregunta
        created_evaluations: list[Evaluation] = []
        now = datetime.utcnow().isoformat()
        evaluator_boleta = alumno["boleta"]
        evaluator_name = alumno.get("nombre") or evaluator_boleta

        for entry in data.scores:
            criterion = criteria_by_id[entry.criteria_id]
            answer_value, score_given = self._resolve_answer(criterion, entry)

            evaluation = Evaluation(
                exposition_id=exposition.id,
                criteria_id=entry.criteria_id,
                evaluator_name=evaluator_name,
                evaluator_boleta=evaluator_boleta,
                answer_value=answer_value,
                score_given=score_given,
                created_at=now,
            )
            self.session.add(evaluation)
            created_evaluations.append(evaluation)

        await self.session.commit()
        for evaluation in created_evaluations:
            await self.session.refresh(evaluation)

        return created_evaluations



