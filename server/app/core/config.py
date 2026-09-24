from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    FRONTEND_URL: str = "http://localhost:5173"

    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_FOLDER: str = ""

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 50

    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024
    UPLOAD_URL_EXPIRY_SECONDS: int = 900

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_SSL: bool = False
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    ASSISTANT_NAME: str = "Luminara"
    ASSISTANT_INSTITUTION: str = "Classroom Dashboard"
    ASSISTANT_MAX_TOOL_TURNS: int = 6
    ASSISTANT_HISTORY_LIMIT: int = 12

    @property
    def sqlalchemy_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.FRONTEND_URL.split(",") if o.strip()]

    @property
    def storage_enabled(self) -> bool:
        return bool(
            self.CLOUDINARY_CLOUD_NAME
            and self.CLOUDINARY_API_KEY
            and self.CLOUDINARY_API_SECRET
        )

    @property
    def assistant_enabled(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def mail_enabled(self) -> bool:
        return bool(self.SMTP_HOST and (self.SMTP_FROM or self.SMTP_USER))

    @property
    def frontend_origin(self) -> str:
        origins = self.cors_origins
        return origins[0] if origins else "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
