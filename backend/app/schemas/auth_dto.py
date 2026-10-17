"""
Capa Schemas - DTOs (Data Transfer Objects)
auth_dto.py: Clases Pydantic para el registro y login de profes (correo/contraseña)
y alumnos (boleta/contraseña), y para la respuesta con el token de acceso.
"""
from pydantic import BaseModel, EmailStr, Field


# --- Profesor / Host (correo + contraseña) ---
class ProfeRegister(BaseModel):
    """Registro de un profe con correo y contraseña."""
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class ProfeLogin(BaseModel):
    """Login de un profe con correo y contraseña."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


# --- Alumno (registro con correo + contraseña + boleta; login con boleta) ---
class AlumnoRegister(BaseModel):
    """Registro de un alumno: correo, contraseña, boleta y nombre."""
    boleta: str = Field(..., min_length=1, max_length=20)
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=6, max_length=128)


class AlumnoLogin(BaseModel):
    """Login de un alumno con boleta y contraseña."""
    boleta: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=1, max_length=128)


# --- Respuestas ---
class HostUserResponse(BaseModel):
    id: str
    email: str | None = None


class AlumnoResponse(BaseModel):
    boleta: str
    email: str
    nombre: str


class HostTokenResponse(BaseModel):
    """Token de acceso emitido para un profe tras login/registro con contraseña."""
    access_token: str
    token_type: str = "bearer"
    user: HostUserResponse


class AlumnoTokenResponse(BaseModel):
    """Token de acceso emitido para un alumno tras login/registro."""
    access_token: str
    token_type: str = "bearer"
    alumno: AlumnoResponse
