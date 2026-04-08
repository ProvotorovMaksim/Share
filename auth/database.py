# app/database.py
"""
Асинхронный движок для основного бота.
Использует общий Base из models_base.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from redaktorsha.config import load_settings
from redaktorsha.auth.models_base import Base

settings = load_settings()

# Async engine для основного бота (asyncpg)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для FastAPI / бота: выдаёт async-сессию.
    
    Usage:
        async for db in get_db():
            # используем db
    """
    async with AsyncSessionLocal() as session:
        yield session