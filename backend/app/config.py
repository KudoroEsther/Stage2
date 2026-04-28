import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Insighta Labs+ Backend")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./insighta.db")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "change-me")
    github_client_id: str = os.getenv("GITHUB_CLIENT_ID", "")
    github_client_secret: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    github_oauth_url: str = os.getenv(
        "GITHUB_OAUTH_URL",
        "https://github.com/login/oauth/authorize",
    )
    github_token_url: str = os.getenv(
        "GITHUB_TOKEN_URL",
        "https://github.com/login/oauth/access_token",
    )
    github_user_url: str = os.getenv("GITHUB_USER_URL", "https://api.github.com/user")
    github_email_url: str = os.getenv(
        "GITHUB_EMAIL_URL",
        "https://api.github.com/user/emails",
    )
    access_token_ttl_seconds: int = int(
        os.getenv("ACCESS_TOKEN_TTL_SECONDS", "180")
    )
    refresh_token_ttl_seconds: int = int(
        os.getenv("REFRESH_TOKEN_TTL_SECONDS", "300")
    )
    auth_rate_limit_per_minute: int = int(
        os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "10")
    )
    api_rate_limit_per_minute: int = int(
        os.getenv("API_RATE_LIMIT_PER_MINUTE", "60")
    )
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
        if origin.strip()
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
