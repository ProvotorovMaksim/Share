# src/redaktorsha/auth/auth_database.py
"""
Синхронный движок для auth-операций.
Использует общий Base из models_base — те же модели, другой движок.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from redaktorsha.auth.models_base import Base  # 🔥 Тот же Base, что и в app/database.py


from redaktorsha.config import load_settings

_settings = load_settings()
_DATABASE_URL = _settings.database_url
_APP_ENV = _settings.app_env

def _convert_to_sync_url(async_url: str) -> str:
    """postgresql+asyncpg://... → postgresql+psycopg2://..."""
    return async_url.replace("postgresql+asyncpg", "postgresql+psycopg2")


# Sync engine ТОЛЬКО для auth (изолированный пул соединений)
auth_engine = create_engine(
    _convert_to_sync_url(_DATABASE_URL),
    echo=(_APP_ENV == "dev"),
    poolclass=NullPool,
    pool_pre_ping=True,
)

AuthSessionLocal = sessionmaker(
    bind=auth_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# Логирование запросов в dev-режиме
if _APP_ENV == "dev":
    @event.listens_for(auth_engine, "before_cursor_execute")
    def _log_query(conn, cursor, statement, params, context, executemany):
        preview = statement.strip()[:200].replace("\n", " ")
        print(f"[AUTH_DB] {preview}...")