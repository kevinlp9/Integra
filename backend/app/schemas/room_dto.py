"""
Capa Schemas - DTOs (Data Transfer Objects)
room_dto.py: Clases Pydantic para validación de JSON de entrada/salida
"""
from pydantic import BaseModel, Field
from typing import Optional


class RoomCreate(BaseModel):
    """DTO para crear una nueva Sala - Datos que el cliente envía"""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    password: Optional[str] = Field(None, min_length=4, max_length=50)


class RoomUpdate(BaseModel):
    """DTO para actualizar una Sala"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    password: Optional[str] = Field(None, min_length=4, max_length=50)


class RoomResponse(BaseModel):
    """DTO para la respuesta al cliente - Datos que serán enviados"""

    id: int
    code: str
    name: str
    description: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True  # Permite convertir modelos SQLModel a Pydantic


class RoomDetailResponse(RoomResponse):
    """DTO extendido con más información"""
    updated_at: Optional[str] = None

