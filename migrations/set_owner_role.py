# src/redaktorsha/fix_owner_role.py
"""
Исправляет роль Owner для указанного Telegram ID.

Запуск:
    python -m src.redaktorsha.fix_owner_role
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from redaktorsha.config import load_settings

def fix_owner_role():
    """Устанавливает роль OWNER для ID из TELEGRAM_OWNER_IDS."""
    settings = load_settings()
    
    # Конвертируем asyncpg URL в psycopg2
    db_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(db_url)
    
    owner_ids = settings.owner_telegram_ids
    
    print(f"🔌 Connecting to database...")
    print(f"👑 Setting OWNER role for: {owner_ids}")
    
    with engine.connect() as conn:
        for owner_id in owner_ids:
            # Проверяем, существует ли пользователь
            result = conn.execute(text(f"""
                SELECT telegram_id, role, username FROM users 
                WHERE telegram_id = {owner_id}
            """)).fetchone()
            
            if result:
                old_role = result[1]
                username = result[2]
                
                # Обновляем роль
                conn.execute(text(f"""
                    UPDATE users SET role = 'OWNER', is_approved = TRUE 
                    WHERE telegram_id = {owner_id}
                """))
                conn.commit()
                
                print(f"✅ Updated: @{username or 'N/A'} ({owner_id})")
                print(f"   Role: {old_role} → OWNER")
            else:
                print(f"⚠️ User {owner_id} not found in database.")
                print(f"   Register first, then run this script again.")
        
        # Показываем итоговое распределение ролей
        result = conn.execute(text("""
            SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY role
        """)).fetchall()
        
        print("\n📊 Role distribution:")
        for row in result:
            print(f"   {row[0]}: {row[1]} users")
        
        print("\n✅ Fix completed!")

if __name__ == "__main__":
    fix_owner_role()