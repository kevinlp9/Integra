"""
Capa API - Routes (Controladores)
room_router.py: Endpoints REST HTTP para Salas, Rúbricas, Exposiciones y Reportes
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_current_teacher_id, get_current_alumno
from app.models.room import Room
from app.schemas.report_dto import RoomReport
from app.schemas.room_dto import (
    RoomCreate,
    RoomResponse,
    RoomJoinResponse,
    AlumnoRoomSummary,
    RubricCriterionCreate,
    RubricCriterionResponse,
    ExpositionCreate,
    ExpositionResponse,
)
from app.services.report_service import ReportService
from app.services.room_service import RoomService

router = APIRouter(
    prefix="/api/rooms",
    tags=["rooms"],
)


async def _get_owned_room(room_id: int, service: RoomService, teacher_id: UUID) -> Room:
    """Obtiene una sala validando que pertenezca al profesor autenticado"""
    room = await service.get_room_by_id(room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sala no encontrada")
    if room.teacher_id != teacher_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta sala")
    return room


# ---------------------------------------------------------------------------
# Rutas de Profesor (requieren JWT de Supabase)
# ---------------------------------------------------------------------------

@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: RoomCreate,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Crea una nueva sala y genera un join_code"""
    service = RoomService(session)
    room = await service.create_room(room_data, teacher_id)
    return room


@router.get("", response_model=list[RoomResponse])
async def list_my_rooms(
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Lista todas las salas del profesor autenticado"""
    service = RoomService(session)
    rooms = await service.list_rooms_by_teacher(teacher_id)
    return rooms


@router.post("/{room_id}/rubric", response_model=RubricCriterionResponse, status_code=status.HTTP_201_CREATED)
async def add_rubric_criterion(
    room_id: int,
    criterion_data: RubricCriterionCreate,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Agrega una pregunta/criterio (rating, multiple_choice, true_false u open_text) a la sala"""
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)
    criterion = await service.add_rubric_criterion(room_id, criterion_data)
    return criterion


@router.get("/{room_id}/rubric", response_model=list[RubricCriterionResponse])
async def list_rubric_criteria(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Lista las preguntas/criterios de evaluación de la sala (incluye correct_answer, solo para el profesor)"""
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)
    return await service.list_rubric_criteria(room_id)


@router.post("/{room_id}/expositions", response_model=ExpositionResponse, status_code=status.HTTP_201_CREATED)
async def add_exposition(
    room_id: int,
    exposition_data: ExpositionCreate,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Registra un elemento evaluable (equipo, jugador, proyecto, ronda) en la sala"""
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)
    exposition = await service.add_exposition(room_id, exposition_data)
    return exposition


@router.get("/{room_id}/expositions", response_model=list[ExpositionResponse])
async def list_expositions(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Lista los elementos evaluables (equipos/jugadores/rondas) de la sala"""
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)
    return await service.list_expositions(room_id)


@router.put("/{room_id}/start", response_model=RoomResponse)
async def start_room(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Inicia la sesión (estilo Kahoot): pasa la sala a 'active' y activa el primer elemento"""
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)

    try:
        room = await service.start_room(room_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return room


@router.put("/{room_id}/next", response_model=RoomResponse)
async def next_exposition(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """
    Avanza al siguiente elemento evaluable en orden (botón "Siguiente" estilo Kahoot).
    Si ya no hay más elementos, finaliza la sala automáticamente y congela los puntajes.
    """
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)

    try:
        room, has_next = await service.activate_next(room_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not has_next:
        report_service = ReportService(session)
        await report_service.freeze_all_scores(room_id)

    return room


@router.put("/{room_id}/activate/{exposition_id}", response_model=RoomResponse)
async def activate_exposition(
    room_id: int,
    exposition_id: int,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Salto manual: activa un elemento evaluable específico (sin seguir el orden)"""
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)

    room = await service.activate_exposition(room_id, exposition_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El elemento indicado no existe en esta sala",
        )
    return room


@router.put("/{room_id}/finish", response_model=RoomResponse)
async def finish_room(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Finaliza la sesión (pantalla final/podio estilo Kahoot) y congela los puntajes finales"""
    service = RoomService(session)
    await _get_owned_room(room_id, service, teacher_id)

    room = await service.finish_room(room_id)

    report_service = ReportService(session)
    await report_service.freeze_all_scores(room_id)

    return room


@router.get("/{room_id}/report", response_model=RoomReport)
async def get_room_report(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    teacher_id: UUID = Depends(get_current_teacher_id),
):
    """Devuelve el DTO consolidado con el ranking (leaderboard) y desglose de calificaciones"""
    room_service = RoomService(session)
    room = await _get_owned_room(room_id, room_service, teacher_id)

    report_service = ReportService(session)
    report = await report_service.build_room_report(room)
    return report


# ---------------------------------------------------------------------------
# Rutas del Alumno (requieren login de alumno: boleta + contraseña)
# ---------------------------------------------------------------------------

async def _build_join_response(room: Room, service: RoomService) -> RoomJoinResponse:
    """Construye el estado actual de la sala (elemento activo + rúbrica pública)."""
    rubric = await service.list_rubric_criteria(room.id)

    current_exposition = None
    if room.current_exposition_id:
        current_exposition = await service.get_exposition_by_id(room.current_exposition_id)

    return RoomJoinResponse(
        room_id=room.id,
        room_name=room.name,
        room_status=room.status,
        is_exposition_active=current_exposition is not None,
        current_exposition=current_exposition,
        rubric=rubric,
    )


@router.get("/mis-salas", response_model=list[AlumnoRoomSummary])
async def list_my_alumno_rooms(
    session: AsyncSession = Depends(get_db_session),
    alumno: dict = Depends(get_current_alumno),
):
    """Lista las salas a las que el alumno autenticado se ha unido ('Mis salas')."""
    service = RoomService(session)
    rooms = await service.list_rooms_by_alumno(alumno["boleta"])
    return [
        AlumnoRoomSummary(
            room_id=room.id,
            name=room.name,
            join_code=room.join_code,
            status=room.status,
        )
        for room in rooms
    ]


@router.post("/join/{join_code}", response_model=RoomJoinResponse)
async def enroll_in_room(
    join_code: str,
    session: AsyncSession = Depends(get_db_session),
    alumno: dict = Depends(get_current_alumno),
):
    """
    El alumno se une a una sala con su código: registra la membresía (idempotente)
    y devuelve el estado actual. Requiere login de alumno (boleta + contraseña).
    """
    service = RoomService(session)
    room = await service.enroll_alumno(join_code, alumno["boleta"])
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código de sala inválido")

    return await _build_join_response(room, service)


@router.get("/join/{join_code}", response_model=RoomJoinResponse)
async def join_room(
    join_code: str,
    session: AsyncSession = Depends(get_db_session),
    alumno: dict = Depends(get_current_alumno),
):
    """
    Devuelve el estado actual de la sala (para el sondeo en vivo). Requiere login
    de alumno Y que el alumno ya se haya unido a esta sala con su código; de lo
    contrario responde 403 (no puede ver salas a las que no ha sido invitado).
    """
    service = RoomService(session)
    room = await service.get_room_by_join_code(join_code)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Código de sala inválido")

    if not await service.is_alumno_enrolled(room.id, alumno["boleta"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No estás inscrito en esta sala. Únete primero con el código.",
        )

    return await _build_join_response(room, service)








