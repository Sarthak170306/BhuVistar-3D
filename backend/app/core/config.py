from pathlib import Path
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base paths for robust .env file discovery
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """
    Centralized application settings loaded from environment variables and root .env file.
    All secrets and environment-specific configs must be loaded dynamically.
    Never commit real secrets or hard-code credentials.
    """

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_ROOT / ".env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project Metadata
    PROJECT_NAME: str = "BhuVistaar 3D"
    DESCRIPTION: str = "3D digital property and vertical land mapping platform"
    VERSION: str = "0.1.0"
    API_BASE_URL: str = "http://localhost:8000"

    # PostgreSQL + PostGIS Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5433
    POSTGRES_USER: str = "sih_user"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "sih_ulpin"

    # Database Connection URL (resolved conceptually to: postgresql+psycopg://sih_user:<password>@localhost:5433/sih_ulpin)
    DATABASE_URL: Optional[str] = None

    # Database Engine Pool Configuration
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # Cesium Ion Token (Placeholder - empty by default, no default API key)
    CESIUM_ION_TOKEN: str = ""

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if v and isinstance(v, str) and v.strip():
            return v.strip()
        data = info.data
        user = data.get("POSTGRES_USER", "sih_user")
        password = data.get("POSTGRES_PASSWORD", "")
        server = data.get("POSTGRES_SERVER", "localhost")
        port = data.get("POSTGRES_PORT", 5433)
        db = data.get("POSTGRES_DB", "sih_ulpin")
        return f"postgresql+psycopg://{user}:{password}@{server}:{port}/{db}"

    @property
    def masked_database_url(self) -> str:
        """
        Returns the database URL with the password redacted for secure logging and display.
        """
        if not self.DATABASE_URL:
            return ""
        try:
            from urllib.parse import urlsplit, urlunsplit
            parts = urlsplit(self.DATABASE_URL)
            if parts.password:
                netloc = parts.netloc.replace(f":{parts.password}@", ":****@")
                return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
            return self.DATABASE_URL
        except Exception:
            return "postgresql+psycopg://<redacted>@localhost:5433/sih_ulpin"


# Centralized settings singleton
settings = Settings()
