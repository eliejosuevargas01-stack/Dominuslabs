import os
from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Hub"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database (No DB creation per instructions, using a placeholder string)
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"

    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "uploads"))

    class Config:
        case_sensitive = True

settings = Settings()