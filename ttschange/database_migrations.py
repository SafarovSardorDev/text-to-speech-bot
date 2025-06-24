import sqlite3
import os

def migrate_database():
    """Mavjud ma'lumotlar bazasini yangi strukturaga o'tkazish"""
    
    if not os.path.exists("main.db"):
        print("❌ main.db fayli topilmadi")
        return
    
    try:
        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()
        
        # Mavjud jadval strukturasini tekshirish
        cursor.execute("PRAGMA table_info(Users)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📊 Mavjud ustunlar: {columns}")
        
        # Agar eski ustunlar mavjud bo'lsa, ularni o'chirish
        if 'created_at' in columns or 'updated_at' in columns:
            print("🔄 Eski jadval strukturasini yangilash...")
            
            # Yangi jadval yaratish
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    voice TEXT DEFAULT 'women'
                );
            """)
            
            # Eski ma'lumotlarni ko'chirish
            cursor.execute("""
                INSERT OR IGNORE INTO Users_new (id, user_id, name, voice)
                SELECT id, user_id, name, voice FROM Users;
            """)
            
            # Eski jadvalni o'chirish
            cursor.execute("DROP TABLE Users;")
            
            # Yangi jadvalni qayta nomlash
            cursor.execute("ALTER TABLE Users_new RENAME TO Users;")
            
            # Index qo'shish
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON Users(user_id);")
            
            conn.commit()
            print("✅ Ma'lumotlar bazasi muvaffaqiyatli yangilandi!")
        else:
            print("✅ Ma'lumotlar bazasi allaqachon to'g'ri strukturada")
            
    except Exception as e:
        print(f"❌ Migration xatolik: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()