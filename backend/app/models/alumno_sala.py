"""
Capa Models - Modelos de Base de Datos
alumno_sala.py: Entidad de membresía Alumno <-> Sala.

Registra a qué salas se ha unido cada alumno (mediante el join_code). Sirve
para construir la lista de "Mis salas" del alumno y para garantizar que solo
vea las salas a las que efectivamente entró.
"""
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import SQLModel, Field


class AlumnoSala(SQLModel, table=True):
    """Relación alumno-sala: una fila por cada sala a la que el alumno se unió."""

    __tablename__ = "alumno_salas"
    __table_args__ = (
        UniqueConstraint("boleta", "room_id", name="uq_alumno_sala"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    # Boleta del alumno (FK lógica -> alumnos.boleta).
    boleta: str = Field(index=True, max_length=20)
    # Sala a la que se unió (FK lógica -> rooms.id).
    room_id: int = Field(index=True)
    # Marca de tiempo de la primera vez que se unió.
    joined_at: str
