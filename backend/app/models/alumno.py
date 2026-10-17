"""
Capa Models - Modelos de Base de Datos
alumno.py: Entidad SQLModel para los alumnos evaluadores.

El alumno se registra con correo, contraseña y boleta, pero inicia sesión
usando su boleta + contraseña. La boleta es el identificador con el que se
vinculan sus evaluaciones (ver Evaluation.evaluator_boleta).
"""
from typing import Optional

from sqlmodel import SQLModel, Field


class Alumno(SQLModel, table=True):
    """Modelo de base de datos para un alumno evaluador"""

    __tablename__ = "alumnos"

    # Número de boleta: identificador académico y clave primaria del alumno.
    boleta: str = Field(primary_key=True, index=True, max_length=20)
    # Correo capturado en el registro (único).
    email: str = Field(unique=True, index=True)
    # Nombre completo del alumno (se usa como evaluator_name en las evaluaciones).
    nombre: str
    # Hash bcrypt de la contraseña.
    hashed_password: str
    created_at: Optional[str] = None
