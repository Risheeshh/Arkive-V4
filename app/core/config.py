from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Bookmark API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/bookmarks"
    REDIS_URL: str = "redis://redis:6379/0"
    TEST_DATABASE_URL: str | None = None
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
