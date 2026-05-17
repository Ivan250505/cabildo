from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Base de datos
    DATABASE_URL: str

    # Seguridad
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FERNET_KEY: str

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    # Google Drive
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/drive/callback"

    # DANE
    DANE_API_BASE_URL: str = "https://www.datos.gov.co/resource/"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "EtnoSIG <noreply@simonky.com>"

    # Almacenamiento
    FILES_BASE_PATH: str = "./storage/files"
    TEMP_PATH: str = "./storage/temp"

    # NLP / SIG
    SPACY_MODEL: str = "es_core_news_lg"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEFAULT_BUFFER_METROS: int = 50

    # Entorno
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
