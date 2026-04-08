# src/redaktorsha/auth_service.py
"""
Auth service module — авторизация с ролевой системой (Owner/Admin/User).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..config import load_settings
from .auth_database import AuthSessionLocal
from .models import User, UserRole
from .security import verify_password, get_password_hash, create_access_token, decode_token

log = logging.getLogger(__name__)


class AuthResult:
    """Результат операции авторизации."""
    
    def __init__(
        self,
        success: bool,
        access_token: Optional[str] = None,
        error: Optional[str] = None,
        user_info: Optional[dict] = None,
        is_pending: bool = False,
        role: str = "user"
    ):
        self.success = success
        self.access_token = access_token
        self.error = error
        self.user_info = user_info
        self.is_pending = is_pending
        self.role = role
    
    def __repr__(self) -> str:
        return f"AuthResult(success={self.success}, role={self.role}, pending={self.is_pending})"


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    """Находит пользователя по telegram_id."""
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def get_all_users(db: Session) -> list[User]:
    """Возвращает всех пользователей."""
    return db.query(User).order_by(User.created_at.desc()).all()


def get_users_by_role(db: Session, role: UserRole) -> list[User]:
    """Возвращает пользователей по роли."""
    return db.query(User).filter(User.role == role).all()


def get_pending_users(db: Session) -> list[User]:
    """Возвращает пользователей, ожидающих одобрения."""
    return db.query(User).filter(
        User.is_approved == False,
        User.is_locked == False
    ).order_by(User.created_at.desc()).all()


def create_user(
    db: Session,
    telegram_id: int,
    username: str,
    password: str,
    reason: Optional[str] = None,
    role: UserRole = UserRole.USER
) -> User:
    """Создаёт нового пользователя."""
    existing = get_user_by_telegram_id(db, telegram_id)
    if existing:
        raise ValueError("User already exists")
    
    settings = load_settings()
    is_owner = telegram_id in settings.owner_telegram_ids
    
    db_user = User(
        telegram_id=telegram_id,
        username=username,
        password_hash=get_password_hash(password),
        role=UserRole.OWNER if is_owner else role,
        is_approved=True if is_owner else False,
        is_locked=False,
        registration_reason=reason,
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def set_user_role(
    db: Session,
    telegram_id: int,
    new_role: UserRole,
    changed_by: int
) -> Optional[User]:
    """Изменяет роль пользователя (только Owner может назначать Admin)."""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    
    user.role = new_role
    user.is_approved = True
    db.commit()
    db.refresh(user)
    return user


def approve_user(
    db: Session,
    telegram_id: int,
    approved_by: int
) -> Optional[User]:
    """Одобряет пользователя."""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    
    user.is_approved = True
    user.approved_by = approved_by
    user.approved_at = datetime.now(timezone.utc)
    user.is_locked = False
    db.commit()
    db.refresh(user)
    return user


def reject_user(db: Session, telegram_id: int) -> Optional[User]:
    """Отклоняет пользователя (помечает как locked)."""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    
    user.is_locked = True
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, telegram_id: int) -> bool:
    """Удаляет пользователя."""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return False
    
    if user.role == UserRole.OWNER:
        raise ValueError("Cannot delete owner account")
    
    db.delete(user)
    db.commit()
    return True


async def auth_register(
    telegram_id: int,
    username: str,
    password: str,
    reason: Optional[str] = None
) -> AuthResult:
    """Регистрация нового пользователя."""
    if len(password) < 8:
        return AuthResult(success=False, error="Password too short (min 8 chars)")
    
    db = AuthSessionLocal()
    try:
        user = create_user(db, telegram_id, username, password, reason)
        return AuthResult(
            success=True,
            is_pending=not user.is_approved,
            role=user.role.value,
            user_info={"telegram_id": user.telegram_id, "username": user.username}
        )
    except ValueError as e:
        return AuthResult(success=False, error=str(e))
    finally:
        db.close()


async def auth_login(telegram_id: int, password: str) -> AuthResult:
    """Вход пользователя с проверкой роли и статуса."""
    db = AuthSessionLocal()
    try:
        user = get_user_by_telegram_id(db, telegram_id)
        
        if not user:
            return AuthResult(success=False, error="Invalid credentials")
        
        if not verify_password(password, user.password_hash):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            user.last_failed_login = datetime.now(timezone.utc)
            db.commit()
            return AuthResult(success=False, error="Invalid credentials")
        
        if user.is_locked:
            return AuthResult(success=False, error="Account is locked. Contact admin.")
        
        if user.role == UserRole.USER and not user.is_approved:
            return AuthResult(
                success=False,
                is_pending=True,
                role=user.role.value,
                error="Account pending approval. Please wait for admin."
            )
        
        user.failed_attempts = 0
        db.commit()
        
        token = create_access_token(
            data={
                "sub": str(user.telegram_id),
                "telegram_id": user.telegram_id,
                "role": user.role.value
            }
        )
        
        return AuthResult(
            success=True,
            access_token=token,
            role=user.role.value,
            user_info={"telegram_id": user.telegram_id, "username": user.username}
        )
    finally:
        db.close()


async def auth_verify_token(token: str) -> Optional[dict]:
    """Проверка валидности JWT-токена."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    
    telegram_id = payload.get("telegram_id")
    if not telegram_id:
        return None
    
    db = AuthSessionLocal()
    try:
        user = get_user_by_telegram_id(db, int(telegram_id))
        if not user:
            return None
        if user.is_locked:
            return None
        if user.role == UserRole.USER and not user.is_approved:
            return None
        
        return {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "role": user.role.value
        }
    finally:
        db.close()


# ────────────────────────────────────────────────────────────────
# Проверки прав доступа
# ────────────────────────────────────────────────────────────────

def can_manage_users(user_role: UserRole) -> bool:
    """Может ли управлять пользователями (Owner + Admin)."""
    return user_role in (UserRole.OWNER, UserRole.ADMIN)


def can_manage_admins(user_role: UserRole) -> bool:
    """Может ли управлять админами (только Owner)."""
    return user_role == UserRole.OWNER


def can_delete_user(user_role: UserRole, target_role: UserRole) -> bool:
    """Может ли удалить пользователя."""
    if user_role == UserRole.OWNER:
        return target_role != UserRole.OWNER
    if user_role == UserRole.ADMIN:
        return target_role == UserRole.USER
    return False


def can_change_role(user_role: UserRole, target_role: UserRole, new_role: UserRole) -> bool:
    """Может ли изменить роль пользователя."""
    if user_role == UserRole.OWNER:
        return True
    if user_role == UserRole.ADMIN:
        return target_role == UserRole.USER and new_role == UserRole.USER
    return False