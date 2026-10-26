from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # для приложения (asyncpg)
    database_url: str = "postgresql+asyncpg://payments:payments@localhost:5432/payments"
    # для Alembic (psycopg, синхронно)
    alembic_database_url: str = "postgresql+psycopg://payments:payments@localhost:5432/payments"

    webhook_secret: str = "dev-secret"


settings = Settings()