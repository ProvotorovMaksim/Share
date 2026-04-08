# src/redaktorsha/init_auth_db.py
"""
Скрипт инициализации БД для auth-модуля.

Запуск:
    1. venv\Scripts\activate
    2. cd src/redaktorsha
    3. python init_auth_db.py
"""
import sys
import os
from pathlib import Path

# 🔥 ВАЖНО: Загружаем .env файл перед чтением переменных!
from dotenv import load_dotenv

# Загружаем .env из текущей папки
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Добавляем src/ в path для импортов
SRC_DIR = Path(__file__).parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main():
    print("🔐 Initializing auth database...")
    
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker, declarative_base
        
        # 🔥 Теперь os.environ видит переменные из .env
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print("⚠️ DATABASE_URL not set — please add to .env file")
            print(f"💡 Checked path: {dotenv_path}")
            sys.exit(1)
        
        # Конвертируем asyncpg → psycopg2 для sync-сессий
        sync_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        print(f"📦 Using database: {sync_url}")
        
        # Создаём sync-движок для auth
        engine = create_engine(
            sync_url,
            echo=False,
            pool_pre_ping=True,
        )
        
        # Общий Base для моделей
        Base = declarative_base()
        
        # Регистрируем модель User (из твоего models.py)
        try:
            from redaktorsha.auth.models import User
            print("✅ Model 'User' imported from redaktorsha.models")
        except ImportError as e:
            print(f"⚠️ Could not import User model: {e}")
            print("📝 Creating fallback User model for testing...")
            
            from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, func
            
            class User(Base):
                __tablename__ = "users"
                id = Column(Integer, primary_key=True, index=True)
                telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
                username = Column(String(64), unique=True, nullable=True)
                password_hash = Column(String(255), nullable=False)
                failed_attempts = Column(Integer, default=0)
                last_failed_login = Column(DateTime(timezone=True), nullable=True)
                is_locked = Column(Boolean, default=False)
                created_at = Column(DateTime(timezone=True), server_default=func.now())
                updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
        
        # Создаём таблицы
        print("📦 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # Проверка подключения и таблицы
        with engine.connect() as conn:
            # ✅ Используем text() для raw SQL (SQLAlchemy 2.0)
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"🔗 Connected to PostgreSQL: '{db_name}'")
            
            # Проверка таблицы users
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
            ))
            exists = result.scalar()
            
            if exists:
                print("✅ Table 'users' exists!")
                
                # Вывод колонок
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position"
                ))
                columns = [row[0] for row in result.fetchall()]
                print(f"📋 Columns: {', '.join(columns)}")
            else:
                print("⚠️ Table 'users' not found")
        
        print("✨ Auth database initialization complete!")
        print("💡 Next step: Run the bot with 'python main.py'")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()