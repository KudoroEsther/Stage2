import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Insighta Labs+ Web")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "change-me")
    secure_cookies: bool = os.getenv("SECURE_COOKIES", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()
