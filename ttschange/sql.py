import sqlite3
import logging
from contextlib import contextmanager

class Database:
    def __init__(self, path_to_db="main.db"):
        self.path_to_db = path_to_db

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = sqlite3.connect(self.path_to_db)
        connection.set_trace_callback(self.logger)
        try:
            yield connection
        except Exception as e:
            connection.rollback()
            logging.error(f"Database xatolik: {e}")
            raise
        finally:
            connection.close()

    def execute(self, sql: str, parameters: tuple = None, fetchone=False, fetchall=False, commit=False):
        """Execute SQL query with proper error handling"""
        if parameters is None:
            parameters = ()
        
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, parameters)
                
                data = None
                if fetchall:
                    data = cursor.fetchall()
                elif fetchone:
                    data = cursor.fetchone()
                
                if commit:
                    connection.commit()
                
                return data
        except sqlite3.Error as e:
            logging.error(f"SQL xatolik: {e}")
            return None

    def create_table_users(self):
        """Create users table if not exists"""
        sql = """
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            voice TEXT DEFAULT 'women'
        );
        """
        
        # Index qo'shish tezlik uchun
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_user_id ON Users(user_id);
        """
        
        try:
            self.execute(sql, commit=True)
            self.execute(index_sql, commit=True)
            logging.info("📊 Users jadvali muvaffaqiyatli yaratildi")
            return True
        except Exception as e:
            logging.error(f"Jadval yaratishda xatolik: {e}")
            return False

    def add_user(self, user_id: int, name: str, voice: str = 'women'):
        """Add new user or ignore if exists"""
        sql = "INSERT OR IGNORE INTO Users(user_id, name, voice) VALUES (?, ?, ?)"
        try:
            result = self.execute(sql, parameters=(user_id, name, voice), commit=True)
            return True
        except Exception as e:
            logging.error(f"Foydalanuvchi qo'shishda xatolik: {e}")
            return False

    def update_user_voice(self, voice: str, user_id: int):
        """Update user's voice preference"""
        sql = "UPDATE Users SET voice = ? WHERE user_id = ?"
        try:
            self.execute(sql, parameters=(voice, user_id), commit=True)
            logging.info(f"✅ Ovoz yangilandi: user_id={user_id}, voice={voice}")
            return True
        except Exception as e:
            logging.error(f"Ovozni yangilashda xatolik: {e}")
            return False

    def get_user_voice(self, user_id: int):
        """Get user's voice preference"""
        sql = "SELECT voice FROM Users WHERE user_id = ?"
        try:
            result = self.execute(sql, parameters=(user_id,), fetchone=True)
            return result[0] if result else 'women'
        except Exception as e:
            logging.error(f"Foydalanuvchi ovozini olishda xatolik: {e}")
            return 'women'

    def stat(self):
        """Get user statistics"""
        try:
            total_users = self.execute("SELECT COUNT(*) FROM Users", fetchone=True)
            male_users = self.execute("SELECT COUNT(*) FROM Users WHERE voice = 'male'", fetchone=True)
            female_users = self.execute("SELECT COUNT(*) FROM Users WHERE voice = 'women'", fetchone=True)
            
            return (total_users[0] if total_users else 0,)  # Tuple formatida qaytarish
        except Exception as e:
            logging.error(f"Statistika olishda xatolik: {e}")
            return (0,)

    def select_all_users(self):
        """Get all users"""
        try:
            return self.execute("SELECT * FROM Users", fetchall=True) or []
        except Exception as e:
            logging.error(f"Barcha foydalanuvchilarni olishda xatolik: {e}")
            return []

    def is_user(self, user_id: int):
        """Check if user exists and return user data"""
        sql = "SELECT * FROM Users WHERE user_id = ?"
        try:
            result = self.execute(sql, parameters=(user_id,), fetchone=True)
            return [result] if result else []  # List formatida qaytarish
        except Exception as e:
            logging.error(f"Foydalanuvchini tekshirishda xatolik: {e}")
            return []

    def delete_user(self, user_id: int):
        """Delete user from database"""
        sql = "DELETE FROM Users WHERE user_id = ?"
        try:
            self.execute(sql, parameters=(user_id,), commit=True)
            return True
        except Exception as e:
            logging.error(f"Foydalanuvchini o'chirishda xatolik: {e}")
            return False

    def get_recent_users(self, limit: int = 10):
        """Get recently added users"""
        sql = "SELECT * FROM Users ORDER BY created_at DESC LIMIT ?"
        try:
            return self.execute(sql, parameters=(limit,), fetchall=True) or []
        except Exception as e:
            logging.error(f"So'nggi foydalanuvchilarni olishda xatolik: {e}")
            return []

    @staticmethod
    def logger(statement):
        """Log SQL statements"""
        logging.debug(f"[SQL] {statement}")

    def backup_database(self, backup_path: str):
        """Create database backup"""
        try:
            with self.get_connection() as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            logging.info(f"✅ Ma'lumotlar bazasi zahiralandi: {backup_path}")
            return True
        except Exception as e:
            logging.error(f"Zahiralashda xatolik: {e}")
            return False

    def optimize_database(self):
        """Optimize database performance"""
        try:
            self.execute("VACUUM", commit=True)
            self.execute("ANALYZE", commit=True)
            logging.info("✅ Ma'lumotlar bazasi optimallashtirildi")
            return True
        except Exception as e:
            logging.error(f"Optimallashtirishda xatolik: {e}")
            return False