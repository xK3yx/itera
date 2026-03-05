import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import JSON, String
from sqlalchemy.types import TypeDecorator
import uuid
from app.main import app
from app.database import get_db, Base
import app.models.roadmap as roadmap_model
import app.models.user as user_model
import app.models.session as session_model
import app.models.message as message_model

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Patch JSONB → JSON for SQLite
class SQLiteJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

# Patch UUID → String for SQLite
class SQLiteUUID(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


def patch_model_columns():
    """Patch PostgreSQL-specific types to SQLite-compatible ones."""
    from sqlalchemy.dialects.postgresql import JSONB, UUID

    for mapper in Base.registry.mappers:
        table = mapper.local_table
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = SQLiteJSON()
            elif isinstance(column.type, UUID):
                column.type = SQLiteUUID()


patch_model_columns()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()