import os
import sqlite3
import time
import bcrypt
from flask import current_app

class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_dir = os.getenv("RENDER_DISK_PATH", "db")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "database.db")
        
        self.db_path = db_path
        self._create_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(username, name)
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                xp INTEGER NOT NULL,
                daily_completion_limit INTEGER NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                task_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                xp_earned INTEGER NOT NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            )
            """)
            conn.commit()

    def get_user(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
            return cursor.fetchone()

    def get_user_by_id(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
            return cursor.fetchone()

    def add_user(self, username, password):
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                          (username, hashed_password.decode('utf-8')))
            conn.commit()

    def delete_user(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def get_all_users(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, xp, level FROM users")
            return cursor.fetchall()

    def get_user_xp_level(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT xp, level FROM users WHERE username = ?", (username,))
            return cursor.fetchone()

    def update_user_xp(self, username, xp_to_add):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT xp, level FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if not user:
                return False
            current_xp, current_level = user["xp"], user["level"]
            new_xp = current_xp + xp_to_add
            required_xp = round(100 * (1.03 ** (current_level - 1)))
            new_level = current_level
            while new_xp >= required_xp:
                new_xp -= required_xp
                new_level += 1
                required_xp = round(100 * (1.03 ** (new_level - 1)))
            cursor.execute(
                "UPDATE users SET xp = ?, level = ? WHERE username = ?",
                (new_xp, new_level, username)
            )
            conn.commit()
            return True

    def add_category(self, username, name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO categories (username, name) VALUES (?, ?)", (username, name))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None

    def delete_category(self, username, category_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE id = ? AND username = ?", (category_id, username))
            if not cursor.fetchone():
                return False
            cursor.execute("DELETE FROM tasks WHERE category_id = ?", (category_id,))
            cursor.execute("DELETE FROM categories WHERE id = ? AND username = ?", (category_id, username))
            conn.commit()
            return True

    def add_task(self, category_id, name, xp, daily_completion_limit):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (category_id, name, xp, daily_completion_limit) VALUES (?, ?, ?, ?)",
                (category_id, name, xp, daily_completion_limit)
            )
            conn.commit()
            return cursor.lastrowid

    def delete_task(self, task_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return True

    def get_all_user_tasks(self, username):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.id, c.name, t.id, t.name, t.xp, t.daily_completion_limit
            FROM categories c
            LEFT JOIN tasks t ON c.id = t.category_id
            WHERE c.username = ?
            ORDER BY c.id, t.id
            """, (username,))
            return cursor.fetchall()

    def record_task_completion(self, username, task_id, xp):
        date = time.strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO task_completions (username, task_id, date, xp_earned) VALUES (?, ?, ?, ?)",
                (username, task_id, date, xp)
            )
            conn.commit()

    def get_daily_xp(self, username, task_id):
        date = time.strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM task_completions WHERE username = ? AND task_id = ? AND date = ?",
                (username, task_id, date)
            )
            result = cursor.fetchone()[0]
            return result if result else 0
        
    def reduce_user_xp(self, user_id, xp_amount):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT xp, level FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                return False
            current_xp, current_level = user["xp"], user["level"]
            new_xp = max(0, current_xp - xp_amount)
            new_level = current_level
            while new_xp < 0 or new_level > 1:
                required_xp = round(100 * (1.03 ** (new_level - 2)))
                if new_xp < required_xp:
                    new_level -= 1
                    new_xp += required_xp
                else:
                    break
            cursor.execute(
                "UPDATE users SET xp = ?, level = ? WHERE id = ?",
                (new_xp, max(1, new_level), user_id)
            )
            conn.commit()
            return True