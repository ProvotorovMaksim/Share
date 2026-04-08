# src/redaktorsha/models.py
"""
Модели базы данных для auth-модуля с ролевой системой.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, func, Text, Enum

from redaktorsha.auth.models_base import Base


class UserRole(enum.Enum):
    """Роли пользователей."""
    OWNER = "owner"      # Полный доступ ко всем функциям
    ADMIN = "admin"      # Управление пользователями
    USER = "user"        # Обычный пользователь


class User(Base):
    """Пользователь с ролевой системой и модерацией."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(64), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    
    # 🔐 Ролевая система
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    # 🔐 Флаги доступа
    is_approved = Column(Boolean, default=False, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    
    # 🔍 Информация для модерации
    registration_reason = Column(Text, nullable=True)
    approved_by = Column(BigInteger, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # 📊 Статистика
    failed_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, role={self.role.value})>"
    
    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER
    
    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.OWNER, UserRole.ADMIN)