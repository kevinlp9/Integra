"""
Capa Services - Lógica de Negocio
report_service.py: Genera el reporte consolidado de una Sala con promedios y desgloses
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.models.exposition import Exposition
from app.models.room import Room
from app.models.rubric import RubricCriterion
from app.schemas.report_dto import CriterionAverage, ExpositionReport, RoomReport


class ReportService:
    """Servicio de negocio para generar reportes consolidados de evaluaciones"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def build_room_report(self, room: Room) -> RoomReport:
        """Construye el DTO consolidado con promedios y desglose de calificaciones"""
        # Obtener criterios de la rúbrica de la sala
        stmt = select(RubricCriterion).where(RubricCriterion.room_id == room.id)
        result = await self.session.execute(stmt)
        criteria = result.scalars().all()

        # Obtener elementos evaluables de la sala
        stmt = select(Exposition).where(Exposition.room_id == room.id).order_by(Exposition.order)
        result = await self.session.execute(stmt)
        expositions = result.scalars().all()

        exposition_reports: list[ExpositionReport] = []

        for exposition in expositions:
            criteria_breakdown: list[CriterionAverage] = []
            exposition_averages: list[float] = []

            for criterion in criteria:
                stmt = select(
                    func.avg(Evaluation.score_given),
                    func.count(Evaluation.score_given),
                ).where(
                    Evaluation.exposition_id == exposition.id,
                    Evaluation.criteria_id == criterion.id,
                )
                result = await self.session.execute(stmt)
                avg_score, total_votes = result.one()
                avg_score = float(avg_score) if avg_score is not None else 0.0

                criteria_breakdown.append(
                    CriterionAverage(
                        criteria_id=criterion.id,
                        name=criterion.name,
                        max_score=criterion.max_score,
                        average_score=round(avg_score, 2),
                        total_votes=total_votes or 0,
                    )
                )
                if total_votes:
                    exposition_averages.append(avg_score)

            final_score = (
                round(sum(exposition_averages) / len(exposition_averages), 2)
                if exposition_averages
                else exposition.final_score
            )

            exposition_reports.append(
                ExpositionReport(
                    exposition_id=exposition.id,
                    name=exposition.name,
                    order=exposition.order,
                    final_score=final_score,
                    criteria_breakdown=criteria_breakdown,
                )
            )

        # Ranking estilo Kahoot: ordenar de mayor a menor final_score y asignar posición.
        # Los elementos sin calificaciones (None) quedan al final.
        exposition_reports.sort(
            key=lambda r: (r.final_score is None, -(r.final_score or 0.0))
        )
        for position, report in enumerate(exposition_reports, start=1):
            report.position = position

        return RoomReport(
            room_id=room.id,
            room_name=room.name,
            room_status=room.status,
            expositions=exposition_reports,
        )

    async def freeze_all_scores(self, room_id: int) -> None:
        """
        Congela el `final_score` de todos los elementos evaluables de la sala,
        calculando el promedio de sus criterios. Se usa al finalizar la sesión
        (estilo pantalla final/podio de Kahoot).
        """
        stmt = select(RubricCriterion).where(RubricCriterion.room_id == room_id)
        result = await self.session.execute(stmt)
        criteria_ids = [c.id for c in result.scalars().all()]

        stmt = select(Exposition).where(Exposition.room_id == room_id)
        result = await self.session.execute(stmt)
        expositions = result.scalars().all()

        for exposition in expositions:
            if not criteria_ids:
                continue

            averages: list[float] = []
            for criteria_id in criteria_ids:
                stmt = select(func.avg(Evaluation.score_given)).where(
                    Evaluation.exposition_id == exposition.id,
                    Evaluation.criteria_id == criteria_id,
                )
                result = await self.session.execute(stmt)
                avg_score = result.scalar_one_or_none()
                if avg_score is not None:
                    averages.append(float(avg_score))

            if averages:
                exposition.final_score = round(sum(averages) / len(averages), 2)

        await self.session.commit()

    async def close_exposition(self, exposition: Exposition, final_score: float) -> Exposition:
        """Congela el resultado final de un elemento evaluable de forma manual"""
        exposition.final_score = final_score
        await self.session.commit()
        await self.session.refresh(exposition)
        return exposition




