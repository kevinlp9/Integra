"""
Capa Services - Lógica de Negocio
room_service.py: Casos de uso puros (sin dependencia del framework web) para Salas,
Rúbricas y Exposiciones.
"""
import secrets
import string
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.room import Room
from app.models.rubric import RubricCriterion
from app.models.exposition import Exposition
from app.models.alumno_sala import AlumnoSala
from app.schemas.room_dto import RoomCreate, RubricCriterionCreate, ExpositionCreate


class RoomService:
    """Servicio de negocio para Salas, Rúbricas y Exposiciones"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _generate_join_code(self) -> str:
        """Genera un código único y corto para unirse a la sala (ej: CALC-1A2B)"""
        suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        return f"ROOM-{suffix}"

    async def create_room(self, room_data: RoomCreate, teacher_id: UUID) -> Room:
        """Crea una nueva Sala y genera un join_code único"""
        db_room = Room(
            teacher_id=teacher_id,
            name=room_data.name,
            join_code=self._generate_join_code(),
            created_at=datetime.utcnow().isoformat(),
        )

        self.session.add(db_room)
        await self.session.commit()
        await self.session.refresh(db_room)

        return db_room

    async def get_room_by_id(self, room_id: int) -> Room | None:
        """Obtiene una sala por su ID"""
        stmt = select(Room).where(Room.id == room_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_room_by_join_code(self, join_code: str) -> Room | None:
        """Obtiene una sala por su join_code"""
        stmt = select(Room).where(Room.join_code == join_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_rooms_by_teacher(self, teacher_id: UUID) -> list[Room]:
        """Lista todas las salas de un profesor"""
        stmt = select(Room).where(Room.teacher_id == teacher_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def enroll_alumno(self, join_code: str, boleta: str) -> Room | None:
        """
        Inscribe al alumno en la sala identificada por su join_code (membresía
        idempotente): si la sala existe y el alumno aún no está inscrito, crea la
        fila en `alumno_salas`. Devuelve la sala, o None si el código es inválido.
        """
        room = await self.get_room_by_join_code(join_code)
        if not room:
            return None

        stmt = select(AlumnoSala).where(
            AlumnoSala.boleta == boleta,
            AlumnoSala.room_id == room.id,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            membership = AlumnoSala(
                boleta=boleta,
                room_id=room.id,
                joined_at=datetime.utcnow().isoformat(),
            )
            self.session.add(membership)
            await self.session.commit()

        return room

    async def list_rooms_by_alumno(self, boleta: str) -> list[Room]:
        """Lista las salas a las que el alumno se ha unido (sus 'Mis salas')."""
        stmt = (
            select(Room)
            .join(AlumnoSala, AlumnoSala.room_id == Room.id)
            .where(AlumnoSala.boleta == boleta)
            .order_by(AlumnoSala.joined_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def is_alumno_enrolled(self, room_id: int, boleta: str) -> bool:
        """Indica si el alumno está inscrito en la sala (ya se unió con el código)."""
        stmt = select(AlumnoSala.id).where(
            AlumnoSala.room_id == room_id,
            AlumnoSala.boleta == boleta,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_rubric_criterion(self, room_id: int, data: RubricCriterionCreate) -> RubricCriterion:
        """Agrega una pregunta/criterio de evaluación a la sala (rating, multiple_choice, true_false u open_text)"""
        criterion = RubricCriterion(
            room_id=room_id,
            name=data.name,
            question_type=data.question_type,
            max_score=data.max_score,
            options=data.options,
            correct_answer=data.correct_answer,
        )
        self.session.add(criterion)
        await self.session.commit()
        await self.session.refresh(criterion)
        return criterion

    async def list_rubric_criteria(self, room_id: int) -> list[RubricCriterion]:
        """Lista los criterios de evaluación de una sala"""
        stmt = select(RubricCriterion).where(RubricCriterion.room_id == room_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add_exposition(self, room_id: int, data: ExpositionCreate) -> Exposition:
        """Registra un elemento evaluable (equipo, jugador, proyecto, ronda) en la sala"""
        order = data.order
        if order is None:
            existing = await self.list_expositions(room_id)
            order = (max((e.order for e in existing), default=0)) + 1

        exposition = Exposition(
            room_id=room_id,
            name=data.name,
            order=order,
            created_at=datetime.utcnow().isoformat(),
        )
        self.session.add(exposition)
        await self.session.commit()
        await self.session.refresh(exposition)
        return exposition

    async def get_exposition_by_id(self, exposition_id: int) -> Exposition | None:
        """Obtiene un elemento evaluable por su ID"""
        stmt = select(Exposition).where(Exposition.id == exposition_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_expositions(self, room_id: int) -> list[Exposition]:
        """Lista los elementos evaluables de una sala, ordenados por turno"""
        stmt = select(Exposition).where(Exposition.room_id == room_id).order_by(Exposition.order)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def activate_exposition(self, room_id: int, exposition_id: int) -> Room | None:
        """
        Cambia el estado de la sala para que los participantes vean la rúbrica
        del elemento (equipo/jugador/ronda) actual. Salto manual a cualquier ítem.
        """
        room = await self.get_room_by_id(room_id)
        if not room:
            return None

        exposition = await self.get_exposition_by_id(exposition_id)
        if not exposition or exposition.room_id != room_id:
            return None

        room.current_exposition_id = exposition.id
        room.status = "active"
        room.updated_at = datetime.utcnow().isoformat()

        await self.session.commit()
        await self.session.refresh(room)

        return room

    async def start_room(self, room_id: int) -> Room | None:
        """
        Inicia la sesión (estilo Kahoot): pasa la sala de 'waiting' a 'active'
        y activa el primer elemento evaluable según su orden.
        """
        room = await self.get_room_by_id(room_id)
        if not room:
            return None

        expositions = await self.list_expositions(room_id)
        if not expositions:
            raise ValueError("La sala no tiene elementos evaluables (expositions) registrados")

        room.status = "active"
        room.current_exposition_id = expositions[0].id
        room.updated_at = datetime.utcnow().isoformat()

        await self.session.commit()
        await self.session.refresh(room)
        return room

    async def activate_next(self, room_id: int) -> tuple[Room | None, bool]:
        """
        Avanza al siguiente elemento evaluable en orden (como el botón "Siguiente"
        de Kahoot). Si ya no hay más, finaliza la sala automáticamente.

        Retorna (room, has_next): has_next=False indica que la sala fue finalizada.
        """
        room = await self.get_room_by_id(room_id)
        if not room:
            return None, False

        expositions = await self.list_expositions(room_id)
        if not expositions:
            raise ValueError("La sala no tiene elementos evaluables (expositions) registrados")

        current_index = None
        for idx, exposition in enumerate(expositions):
            if exposition.id == room.current_exposition_id:
                current_index = idx
                break

        next_index = 0 if current_index is None else current_index + 1

        if next_index >= len(expositions):
            room = await self.finish_room(room_id)
            return room, False

        room.current_exposition_id = expositions[next_index].id
        room.status = "active"
        room.updated_at = datetime.utcnow().isoformat()

        await self.session.commit()
        await self.session.refresh(room)
        return room, True

    async def finish_room(self, room_id: int) -> Room | None:
        """Marca la sala como finalizada (estilo pantalla final/podio de Kahoot)"""
        room = await self.get_room_by_id(room_id)
        if not room:
            return None

        room.status = "finished"
        room.current_exposition_id = None
        room.updated_at = datetime.utcnow().isoformat()

        await self.session.commit()
        await self.session.refresh(room)
        return room





