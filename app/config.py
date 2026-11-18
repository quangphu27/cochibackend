"""Application configuration."""
import os
import re
from datetime import timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Vercel production + preview deployments
VERCEL_ORIGIN = re.compile(r"^https://[\w-]+\.vercel\.app$")

PRODUCTION_FRONTEND_URL = "https://bright-future-english.vercel.app"


def _default_frontend_url() -> str:
    explicit = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    if os.getenv("FLASK_ENV", "development").lower() == "production":
        return PRODUCTION_FRONTEND_URL
    return "http://localhost:5173"


def _build_cors_origins(app_frontend_url: str | None = None) -> list:
    """Allowed browser origins for API (strings + regex patterns)."""
    origins: list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        PRODUCTION_FRONTEND_URL,
        VERCEL_ORIGIN,
    ]
    for url in (
        os.getenv("FRONTEND_URL", "").strip().rstrip("/"),
        (app_frontend_url or "").strip().rstrip("/"),
    ):
        if url and url not in origins:
            origins.append(url)
    for part in os.getenv("CORS_ORIGINS", "").split(","):
        origin = part.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


def origin_allowed(origin: str | None, allowed: list | None = None) -> bool:
    if not origin:
        return False
    for entry in allowed or _build_cors_origins():
        if isinstance(entry, str):
            if origin == entry:
                return True
        elif hasattr(entry, "match") and entry.match(origin):
            return True
    return False


def _db_name_from_uri(uri: str) -> str | None:
    """Extract database name from MongoDB URI path, e.g. .../cochibrightfuture"""
    if not uri:
        return None
    path = urlparse(uri).path.strip("/")
    if not path:
        return None
    return path.split("/")[0].split("?")[0] or None


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB = os.getenv("MONGODB_DB") or _db_name_from_uri(MONGODB_URI) or "cochibrightfuture"

    # Cloudinary: prefer CLOUDINARY_URL (official format)
    CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")
    CLOUDINARY_FOLDER_PREFIX = os.getenv("CLOUDINARY_FOLDER_PREFIX", "cochibrightfuture")

    # Fallback individual keys (optional if CLOUDINARY_URL is set)
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

    FRONTEND_URL = _default_frontend_url()

    # Filled at app startup in create_app(); placeholder for config object
    CORS_ORIGINS: list = []
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    FRONTEND_URL = os.getenv("FRONTEND_URL", PRODUCTION_FRONTEND_URL).strip().rstrip("/")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
