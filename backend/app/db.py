from databases import Database
from sqlalchemy import MetaData, create_engine

from app.config import get_settings


settings = get_settings()
database_url = settings.database_url

if database_url.startswith("postgresql://"):
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    sync_database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg2://",
    )
else:
    async_database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    sync_database_url = database_url


database = Database(async_database_url)
metadata = MetaData()
engine = create_engine(
    sync_database_url,
    connect_args={"check_same_thread": False} if sync_database_url.startswith("sqlite") else {},
)
