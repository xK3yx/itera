"""
Test fixtures.

Tests run against an in-memory SQLite database. PostgreSQL-only column types
(UUID, JSONB, ARRAY) are swapped for SQLite-compatible equivalents before the
schema is created, so no Postgres instance is needed to run the suite.
"""
import os

# Settings are read at import time, so provide test values before importing the app.
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_EMAILS", "admin@example.com")

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator

import app.models  # noqa: F401  registers every model with Base.metadata
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class SQLiteJSON(TypeDecorator):
    impl = JSON
    cache_ok = True


class SQLiteUUID(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(value)

    def process_result_value(self, value, dialect):
        return value


def _patch_postgres_types():
    for mapper in Base.registry.mappers:
        for column in mapper.local_table.columns:
            if isinstance(column.type, (JSONB, ARRAY)):
                column.type = SQLiteJSON()
            elif isinstance(column.type, UUID):
                column.type = SQLiteUUID()


_patch_postgres_types()


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def register(client, email="user@example.com", username="user", password="password123"):
    """Register a user and return auth headers."""
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
