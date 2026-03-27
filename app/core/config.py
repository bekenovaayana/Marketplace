from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "local"
    APP_NAME: str = "marketplace-api"

    # If provided, overrides all DB_* settings (works for MySQL or SQLite).
    DATABASE_URL: str | None = None

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "marketplace"
    DB_PASSWORD: str = "marketplace"
    DB_NAME: str = "marketplace"

    # For local DX: if using SQLite, auto-create tables on startup.
    AUTO_CREATE_DB: bool = True

    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    UPLOADS_DIR: str = "uploads"
    UPLOADS_URL_PREFIX: str = "/uploads"

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.ENV == "local":
            return "sqlite:///./marketplace_local.db"
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()

