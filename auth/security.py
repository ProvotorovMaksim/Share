# src/redaktorsha/security.py
"""
Утилиты безопасности: хеширование паролей и JWT-токены.
Используем argon2 — современный алгоритм без ограничений bcrypt.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import load_settings

log = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# Настройки
# ────────────────────────────────────────────────────────────────

# 🔥 Argon2 — современный алгоритм (нет лимита 72 байта!)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGORITHM = "HS256"

_settings = load_settings()
SECRET_KEY = _settings.jwt_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES = _settings.jwt_access_expire_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        log.warning("Password verify error: %s", e)
        return False


def get_password_hash(password: str) -> str:
    """Хеширует пароль (argon2 принимает любую длину)."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создаёт JWT access-токен."""
    to_encode = data.copy()
    
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Декодирует JWT-токен."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        log.warning("Token decode error: %s", e)
        return None