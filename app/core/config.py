from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    Follows Pydantic v2 BaseSettings specification.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # General API Configuration
    PROJECT_NAME: str = "Geospatial File Measurement API"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Configuration (Default: SQLite local database)
    DATABASE_URL: str = "sqlite:///./data/geospatial.db"

    # Storage Paths
    UPLOAD_DIR: str = "./data/uploads"
    TEMP_DIR: str = "./data/temp"

    # File Upload Limits (50 MB default)
    MAX_UPLOAD_SIZE_MB: int = 50

    # Geospatial Settings
    DEFAULT_PROJECTED_CRS_FALLBACK: str = "EPSG:3857"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of Settings.
    """
    return Settings()
