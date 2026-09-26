"""
Capa API - Routes (Controladores)
room_router.py: Endpoints REST HTTP para gestión de Salas
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db_session, get_current_user
from app.schemas.room_dto import RoomCreate, RoomUpdate, RoomResponse, RoomDetailResponse
from app.services.room_service import RoomService

router = APIRouter(
    prefix="/api/v1/rooms",
    tags=["rooms"],
)


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: RoomCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Crea una nueva Sala de llamadas"""
    service = RoomService(session)
    room = await service.create_room(room_data)
    return room


@router.get("/", response_model=list[RoomResponse])
async def list_rooms(
    skip: int = 0,
    limit: int = 10,
    session: AsyncSession = Depends(get_db_session),
):
    """Lista todas las Salas disponibles"""
    service = RoomService(session)
    rooms = await service.list_rooms(skip, limit)
    return rooms


@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Obtiene los detalles de una Sala específica"""
    service = RoomService(session)
    room = await service.get_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sala no encontrada",
        )
    return room


@router.put("/{room_id}", response_model=RoomDetailResponse)
async def update_room(
    room_id: int,
    room_data: RoomUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Actualiza una Sala existente"""
    service = RoomService(session)
    room = await service.update_room(room_id, room_data)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sala no encontrada",
        )
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    """Elimina una Sala"""
    service = RoomService(session)
    success = await service.delete_room(room_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sala no encontrada",
        )

