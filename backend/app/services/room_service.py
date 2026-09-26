"""
Capa Services - Lógica de Negocio
room_service.py: Casos de uso puros (sin dependencia del framework web)
"""
import secrets
import hashlib
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from passlib.context import CryptContext
from app.models.room import Room
from app.schemas.room_dto import RoomCreate, RoomUpdate

# Configuración de hash para contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RoomService:
    """Servicio de negocio para Salas"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _generate_room_code(self) -> str:
        """Genera un código único y corto para la sala (ej: ABC123)"""
        return secrets.token_hex(3).upper()

    def _hash_password(self, password: str) -> str:
        """Hashea una contraseña"""
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica una contraseña contra su hash"""
        return pwd_context.verify(plain_password, hashed_password)

    async def create_room(self, room_data: RoomCreate) -> Room:
        """
        Crea una nueva sala con validaciones de negocio.
        - Genera un código único
        - Hashea la contraseña si se proporciona
        """
        # Generar código único
        room_code = self._generate_room_code()

        # Crear la entidad
        db_room = Room(
            code=room_code,
            name=room_data.name,
            description=room_data.description,
            password_hash=self._hash_password(room_data.password) if room_data.password else None,
            created_at=datetime.utcnow().isoformat(),
        )

        # Guardar en base de datos
        self.session.add(db_room)
        await self.session.commit()
        await self.session.refresh(db_room)

        return db_room

    async def list_rooms(self, skip: int = 0, limit: int = 10) -> list[Room]:
        """Lista todas las salas activas con paginación"""
        stmt = select(Room).where(Room.is_active == True).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_room_by_id(self, room_id: int) -> Room | None:
        """Obtiene una sala por su ID"""
        stmt = select(Room).where(Room.id == room_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_room_by_code(self, room_code: str) -> Room | None:
        """Obtiene una sala por su código"""
        stmt = select(Room).where(Room.code == room_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_room(self, room_id: int, room_data: RoomUpdate) -> Room | None:
        """Actualiza una sala existente"""
        room = await self.get_room_by_id(room_id)
        if not room:
            return None

        # Actualizar solo los campos proporcionados
        if room_data.name:
            room.name = room_data.name
        if room_data.description is not None:
            room.description = room_data.description
        if room_data.password:
            room.password_hash = self._hash_password(room_data.password)

        room.updated_at = datetime.utcnow().isoformat()

        await self.session.commit()
        await self.session.refresh(room)

        return room

    async def delete_room(self, room_id: int) -> bool:
        """Elimina (soft delete) una sala"""
        room = await self.get_room_by_id(room_id)
        if not room:
            return False

        room.is_active = False
        room.updated_at = datetime.utcnow().isoformat()

        await self.session.commit()
        return True

