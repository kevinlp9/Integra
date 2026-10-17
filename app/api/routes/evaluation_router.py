"""
Capa API - Routes (Controladores)
evaluation_router.py: Endpoint público para la emisión de calificaciones por parte de alumnos
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_alumno, get_db_session
from app.schemas.evaluation_dto import EvaluationSubmit
from app.services.evaluation_service import EvaluationService

router = APIRouter(
    prefix="/api/evaluations",
    tags=["evaluations"],
)


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_evaluation(
    payload: EvaluationSubmit,
    session: AsyncSession = Depends(get_db_session),
    alumno: dict = Depends(get_current_alumno),
):
    """
    Recibe el arreglo de calificaciones emitidas por un alumno para el elemento
    activo. Requiere que el alumno haya iniciado sesión (boleta + contraseña):
    la identidad del evaluador (boleta y nombre) se toma del token, no del body.
    """
    service = EvaluationService(session)
    evaluations = await service.submit_evaluation(payload, alumno)
    return {
        "message": "Evaluación registrada correctamente",
        "count": len(evaluations),
    }

