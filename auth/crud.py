from sqlalchemy.orm import Session
from models import User
from security import hash_password, verify_password, create_access_token, create_refresh_token
from datetime import datetime, timedelta

LOCKOUT_MINUTES = 15
MAX_ATTEMPTS = 5

def get_user(db: Session, telegram_id: int):
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def register_user(db: Session, telegram_id: int, username: str | None, password: str):
    if get_user(db, telegram_id):
        raise ValueError("Пользователь уже существует")
    user = User(
        telegram_id=telegram_id,
        username=username,
        password_hash=hash_password(password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def login_user(db: Session, telegram_id: int, password: str):
    user = get_user(db, telegram_id)
    if not user:
        raise ValueError("Пользователь не найден")

    if user.is_locked:
        if datetime.utcnow() - user.last_failed_login < timedelta(minutes=LOCKOUT_MINUTES):
            raise ValueError(f"Аккаунт заблокирован на {LOCKOUT_MINUTES} минут")
        user.is_locked = False
        user.failed_attempts = 0

    if verify_password(password, user.password_hash):
        user.failed_attempts = 0
        user.is_locked = False
        db.commit()

        access_token = create_access_token({"sub": str(user.telegram_id)})
        refresh_token = create_refresh_token({"sub": str(user.telegram_id)})
        return {"access_token": access_token, "refresh_token": refresh_token}
    else:
        user.failed_attempts += 1
        user.last_failed_login = datetime.utcnow()
        if user.failed_attempts >= MAX_ATTEMPTS:
            user.is_locked = True
        db.commit()
        raise ValueError("Неверный пароль")