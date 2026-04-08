# src/redaktorsha/migrate_add_roles.py
"""
Миграция: добавляет поле role в таблицу users.

Запуск:
    python -m src.redaktorsha.migrate_add_roles
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from redaktorsha.config import load_settings

def migrate():
    """Выполняет миграцию базы данных."""
    settings = load_settings()
    
    # Конвертируем asyncpg URL в psycopg2 для синхронной миграции
    db_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(db_url)
    
    print("🔌 Connecting to database...")
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Добавляем role
        if 'role' not in columns:
            print("📦 Adding column: role")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'user'
            """))
            conn.commit()
            
            # Устанавливаем owner для первого админа из .env
            print("👑 Setting owner role for configured admin...")
            conn.execute(text("""
                UPDATE users SET role = 'owner' 
                WHERE telegram_id = ANY(ARRAY[1182351877]::BIGINT[])
            """))
            conn.commit()
        else:
            print("✅ Column role already exists")
        
        # Обновляем существующие is_approved для админов
        print("🔄 Updating is_approved for existing admins...")
        conn.execute(text("""
            UPDATE users SET is_approved = TRUE, role = 'admin'
            WHERE telegram_id = ANY(ARRAY[1182351877]::BIGINT[])
        """))
        conn.commit()
        
        print("✅ Migration completed!")

if __name__ == "__main__":
    migrate()