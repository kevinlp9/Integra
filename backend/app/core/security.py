"""
Capa Core - Seguridad
security.py: Middleware para decodificar y validar el JWT emitido por Supabase Auth.

El token es generado por Supabase (no por esta API) cuando el profesor hace
login con OAuth2 (ej. "Continuar con Google") desde el frontend. Aquí lo
validamos y extraemos el UUID del profesor (claim "sub") para autorizar
operaciones protegidas.

Soporta los dos esquemas de firma de Supabase:
  1. Nuevo (recomendado): llaves asimétricas (ES256/RS256) publicadas en el
     endpoint JWKS del proyecto: `${SUPABASE_URL}/auth/v1/.well-known/jwks.json`.
     No requiere ningún secreto compartido; se cachea en memoria.
  2. Legado: secreto HS256 compartido (`SUPABASE_JWT_SECRET`), si el proyecto
     aún lo usa. Se intenta primero por ser más rápido (sin llamada de red).
"""
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import httpx
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

# Roles soportados por los tokens emitidos por esta API
ROLE_HOST = "host"      # Profesor que crea y controla salas
ROLE_ALUMNO = "alumno"  # Estudiante evaluador (se identifica por su boleta)


# ---------------------------------------------------------------------------
# Hashing de contraseñas (bcrypt)
# ---------------------------------------------------------------------------
# bcrypt opera sobre un máximo de 72 bytes; passwords más largos se truncan de
# forma segura a esa longitud antes de hashear/verificar.
def hash_password(plain_password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash bcrypt almacenado."""
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Emisión de JWT propios (login con correo/contraseña o boleta/contraseña)
# ---------------------------------------------------------------------------
def create_access_token(subject: str, role: str, extra_claims: dict | None = None) -> str:
    """
    Crea un JWT firmado por esta API.

    - `subject` (claim 'sub'): identificador del usuario. Para el profe es su
      UUID; para el alumno es su boleta.
    - `role`: ROLE_HOST o ROLE_ALUMNO.
    - `extra_claims`: datos adicionales a incluir (ej. email, nombre).
    """
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": subject,
        "role": role,
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# Cache en memoria del JWKS del proyecto (evita golpear la red en cada request)
_JWKS_CACHE: dict = {"keys": [], "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600  # 1 hora


def _jwks_url() -> str:
    return f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"


async def _get_jwks(force_refresh: bool = False) -> list[dict]:
    """Obtiene (con caché) el conjunto de llaves públicas (JWKS) del proyecto Supabase"""
    now = time.time()
    if not force_refresh and _JWKS_CACHE["keys"] and (now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL_SECONDS):
        return _JWKS_CACHE["keys"]

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(_jwks_url())
        response.raise_for_status()
        keys = response.json().get("keys", [])

    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


async def _verify_with_jwks(token: str, kid: str | None) -> dict:
    """Verifica el JWT usando las llaves públicas (asimétricas) del proyecto"""
    keys = await _get_jwks()
    matching_key = next((k for k in keys if k.get("kid") == kid), None)

    if matching_key is None:
        # El 'kid' podría corresponder a una llave rotada recientemente: refrescar caché
        keys = await _get_jwks(force_refresh=True)
        matching_key = next((k for k in keys if k.get("kid") == kid), None)

    if matching_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se encontró la llave pública para validar el token",
        )

    algorithm = matching_key.get("alg", "ES256")
    return jwt.decode(
        token,
        matching_key,
        algorithms=[algorithm],
        audience="authenticated",
        options={"verify_aud": False},
    )


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verifica y decodifica el JWT. Soporta dos emisores:
      1. Esta API (login con correo/contraseña o boleta/contraseña): HS256 con
         `settings.JWT_SECRET` e `iss = settings.JWT_ISSUER`.
      2. Supabase Auth (login con Google): secreto legado HS256 o llaves
         asimétricas publicadas en el JWKS del proyecto.
    """
    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token malformado")

    try:
        # 1) Token propio emitido por esta API (correo/contraseña o boleta/contraseña)
        if header.get("alg") == settings.JWT_ALGORITHM:
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET,
                    algorithms=[settings.JWT_ALGORITHM],
                )
                if payload.get("iss") == settings.JWT_ISSUER:
                    return payload
            except JWTError:
                pass  # No es un token propio válido; se intenta con Supabase.

        # 2) Legado Supabase: secreto HS256 compartido, si está configurado
        if settings.SUPABASE_JWT_SECRET and header.get("alg") == "HS256":
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=[settings.ALGORITHM],
                audience="authenticated",
                options={"verify_aud": False},
            )

        # 3) Supabase nuevo esquema: llaves asimétricas publicadas en el JWKS
        return await _verify_with_jwks(token, header.get("kid"))

    except HTTPException:
        raise
    except (JWTError, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )


def get_teacher_id_from_payload(payload: dict) -> UUID:
    """Extrae el UUID del profesor (claim 'sub') desde el payload del JWT"""
    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene un identificador de usuario válido",
        )
    try:
        return UUID(subject)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuario inválido en el token",
        )


def get_boleta_from_payload(payload: dict) -> str:
    """
    Extrae y valida la boleta del alumno desde un token emitido por esta API.
    Requiere que el token tenga rol de alumno (claim 'role' == ROLE_ALUMNO).
    """
    if payload.get("role") != ROLE_ALUMNO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación requiere una sesión de alumno",
        )
    boleta = payload.get("sub")
    if not boleta:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene una boleta válida",
        )
    return str(boleta)




