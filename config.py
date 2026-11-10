from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_PORT: int = 6379
    REDIS_HOST: str
    REDIS_DB: int = 0
    REDIS_PASSWORD:str
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str
    BROKER: str
    BACKEND: str
    SMTP_USER:str
    SMTP_PORT:str
    SMTP_PASS:str
    SMTP_HOST:str
    CELERY_TIMEZONE: str = "Asia/Shanghai"

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")


Config = Settings()

