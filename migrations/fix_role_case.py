# src/redaktorsha/fix_role_case.py
"""
Исправляет регистр значений role в БД (lowercase → UPPERCASE).

Запуск:
    python -m src.redaktorsha.fix_role_case
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from redaktorsha.config import load_settings

def fix_role_case():
    """Исправляет регистр role в таблице users."""
    settings = load_settings()
    
    # Конвертируем asyncpg URL в psycopg2
    db_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(db_url)
    
    print("🔌 Connecting to database...")
    
    with engine.connect() as conn:
        # Исправляем lowercase → UPPERCASE
        print("🔄 Fixing role case...")
        
        conn.execute(text("""
            UPDATE users SET role = 'OWNER' WHERE role = 'owner'
        """))
        conn.execute(text("""
            UPDATE users SET role = 'ADMIN' WHERE role = 'admin'
        """))
        conn.execute(text("""
            UPDATE users SET role = 'USER' WHERE role = 'user'
        """))
        
        conn.commit()
        
        # Проверяем результат
        result = conn.execute(text("""
            SELECT role, COUNT(*) FROM users GROUP BY role
        """)).fetchall()
        
        print("✅ Role distribution after fix:")
        for row in result:
            print(f"   {row[0]}: {row[1]} users")
        
        print("✅ Fix completed!")

if __name__ == "__main__":
    fix_role_case()