"""Test configuration and fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import URL, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.db.config import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create a test database engine.

    Strategy:
    - Local/Unit testing: uses SQLite in-memory database (no postgres required)
    - CI/Docker: uses DATABASE_URL environment variable if set (postgres)
    - Tables created once per session, tests use transaction rollback
    """
    # Check if DATABASE_URL is set by CI/Docker (use postgres)
    database_url_env = os.environ.get("DATABASE_URL")

    if database_url_env:
        # CI/Docker mode: use PostgreSQL
        print(f"TEST DB: Using CI/Docker mode with DATABASE_URL: {database_url_env}")
        test_db_url = database_url_env

        # Create engine with postgres
        engine = create_async_engine(
            test_db_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            pool_recycle=300,
        )
    else:
        # Local mode: use SQLite in-memory database
        print("TEST DB: Using SQLite in-memory database (no postgres required)")
        test_db_url = "sqlite+aiosqlite:///:memory:"

        # Create engine with SQLite
        engine = create_async_engine(
            test_db_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )

        # Enable foreign key support for SQLite
        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Create all tables once per session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session for testing with transaction rollback.

    Uses nested transactions (savepoints) to isolate each test.
    After the test completes, all changes are rolled back.
    This follows the AGENTS.md requirement to use transaction rollback instead of dropping tables.
    """
    # Create a connection for the test
    connection = await async_engine.connect()

    # Start a transaction
    transaction = await connection.begin()

    # Create session bound to this connection
    async_session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    session = async_session_maker()

    # Start a nested transaction (savepoint)
    await session.begin_nested()

    # Setup automatic savepoint recreation on commit
    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    yield session

    # Rollback everything
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session for testing with transaction rollback.

    Alternative naming convention for test session fixtures.
    Uses the same transaction rollback pattern as async_session.
    """
    # Create a connection for the test
    connection = await async_engine.connect()

    # Start a transaction
    transaction = await connection.begin()

    # Create session bound to this connection
    async_session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    session = async_session_maker()

    # Start a nested transaction (savepoint)
    await session.begin_nested()

    # Setup automatic savepoint recreation on commit
    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    yield session

    # Rollback everything
    await session.close()
    await transaction.rollback()
    await connection.close()
