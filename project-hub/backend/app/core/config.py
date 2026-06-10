import os
from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Dominuslabs"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    # Authentication
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")
    SECRET_KEY: str = os.getenv("JWT_SECRET", "dominuslabs-super-secret-key-2026")

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"))

    # Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Database (SQLite file stored in persistent uploads directory or PostgreSQL if DATABASE_URL is set)
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            # SQLAlchemy expects 'postgresql://' instead of 'postgres://'
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        return f"sqlite:///{os.path.join(self.UPLOAD_DIR, 'dominuslabs.db')}"

    class Config:
        case_sensitive = True

settings = Settings()