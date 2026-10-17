"""
Capa Core - Configuración
Config.py: Carga y valida todas las variables de entorno
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación desde variables de entorno"""

    # Base de datos (PostgreSQL en Supabase, driver asyncpg)
    DATABASE_URL: str

    # Supabase - URL del proyecto (usada para construir el endpoint JWKS de Auth)
    SUPABASE_URL: str

    # Supabase - Nuevas API Keys (reemplazan a anon/service_role)
    SUPABASE_PUBLISHABLE_KEY: str | None = None  # segura para el frontend (con RLS)
    SUPABASE_SECRET_KEY: str | None = None  # solo backend, acceso privilegiado

    # Legacy (opcional): si el proyecto todavía firma JWT con un secreto HS256
    # compartido, se usa como fallback rápido sin llamar al endpoint JWKS.
    SUPABASE_JWT_SECRET: str | None = None
    ALGORITHM: str = "HS256"

    # Autenticación propia: JWT emitido por este backend para el login con
    # correo/contraseña (profe) y boleta/contraseña (alumno). NO lo emite
    # Supabase; se firma con un secreto propio (HS256).
    # IMPORTANTE: define un valor largo y aleatorio en producción (.env).
    JWT_SECRET: str = "CHANGE_ME_super_secret_dev_key"
    JWT_ALGORITHM: str = "HS256"
    # Emisor ("iss") que identifica los tokens generados por esta API, para
    # distinguirlos de los tokens de Supabase durante la verificación.
    JWT_ISSUER: str = "integra-api"
    # Vigencia del token de acceso (en minutos). Por defecto 24 horas.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS - Orígenes exactos permitidos (separados por coma), ej:
    # "http://localhost:3000,https://mi-app.vercel.app"
    # Obligatorio en .env, sin valor por defecto en código.
    ALLOWED_ORIGINS: str

    # CORS - Regex opcional para permitir dominios dinámicos (ej. previews de Vercel)
    # Ej: r"https://.*\.vercel\.app"
    ALLOWED_ORIGIN_REGEX: str | None = None

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


# Instancia global de configuración
settings = Settings()



