"""
Capa Schemas - DTOs (Data Transfer Objects)
report_dto.py: Clases Pydantic para el reporte consolidado de una Sala
"""
from typing import Optional

from pydantic import BaseModel


class CriterionAverage(BaseModel):
    """Promedio de calificaciones para un criterio de la rúbrica"""

    criteria_id: int
    name: str
    max_score: float
    average_score: float
    total_votes: int


class ExpositionReport(BaseModel):
    """Reporte de calificaciones para un elemento evaluable (equipo/jugador/ronda)"""

    exposition_id: int
    name: str
    order: int
    final_score: Optional[float] = None
    position: Optional[int] = None  # Posición en el ranking (1 = primer lugar)
    criteria_breakdown: list[CriterionAverage] = []


class RoomReport(BaseModel):
    """DTO consolidado con el ranking (leaderboard) y desglose de calificaciones de una Sala"""

    room_id: int
    room_name: str
    room_status: str
    expositions: list[ExpositionReport] = []  # Ordenado como ranking (mayor a menor final_score)


