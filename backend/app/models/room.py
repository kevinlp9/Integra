"""
Capa Models - Modelos de Base de Datos
room.py: Entidad SQLModel para la tabla de Salas (mapeo directo a SQL)
"""
from sqlmodel import SQLModel, Field
from typing import Optional


class Room(SQLModel, table=True):
    """Modelo de base de datos para en una Sala de llamadas"""

    __tablename__ = "rooms"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)  # Código único de la sala
    name: str = Field(index=True)
    description: Optional[str] = None
    password_hash: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: str  # Timestamp de creación
    updated_at: Optional[str] = None  # Timestamp de última actualización

