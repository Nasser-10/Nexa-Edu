import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Nexa - AI Educational Marketplace"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "antigravity_super_secret_jwt_key_998234891723491823749")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ai_edu.db")
    
    TEACHER_SHARE_PCT: float = 0.80  # 80%
    PLATFORM_SHARE_PCT: float = 0.20 # 20%
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]
    RATE_LIMIT_PER_MINUTE: int = 120
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    class Config:
        case_sensitive = True

settings = Settings()
