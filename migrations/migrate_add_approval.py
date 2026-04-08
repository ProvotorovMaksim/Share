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
    
    db_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(db_url)
    
    print("🔌 Connecting to database...")
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'role' not in columns:
            print("📦 Adding column: role")
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'user'
            """))
            conn.commit()
            
            print("👑 Setting owner role for configured admin...")
            owner_ids = settings.owner_telegram_ids
            if owner_ids:
                ids_str = ",".join(str(i) for i in owner_ids)
                conn.execute(text(f"""
                    UPDATE users SET role = 'owner', is_approved = TRUE 
                    WHERE telegram_id = ANY(ARRAY[{ids_str}]::BIGINT[])
                """))
                conn.commit()
        else:
            print("✅ Column role already exists")
        
        print("✅ Migration completed!")

if __name__ == "__main__":
    migrate()