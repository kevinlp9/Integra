"""
Capa Core - Migraciones ligeras
migrations.py: Ajustes de esquema idempotentes que se ejecutan al arrancar.

SQLModel/`create_all` crea tablas que no existen, pero NO altera tablas ya
existentes (no agrega columnas nuevas). Para los cambios de autenticación se
necesitan columnas adicionales en tablas que ya viven en Supabase, así que se
aplican aquí con sentencias idempotentes (`ADD COLUMN IF NOT EXISTS`).

Es seguro ejecutarlo en cada arranque: si la columna ya existe, no hace nada.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

# Sentencias DDL idempotentes. PostgreSQL soporta IF NOT EXISTS en ADD COLUMN.
_MIGRATION_STATEMENTS: list[str] = [
    # Profe (host): hash de contraseña para login con correo + contraseña.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password TEXT",
    # Evaluación: boleta del alumno evaluador que la emitió.
    "ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS evaluator_boleta VARCHAR(20)",
]


async def run_startup_migrations(conn: AsyncConnection) -> None:
    """Aplica los ajustes de esquema idempotentes necesarios para la auth propia."""
    for statement in _MIGRATION_STATEMENTS:
        await conn.execute(text(statement))
