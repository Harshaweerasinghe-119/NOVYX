import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("novyx.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                referred_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referred_by)
                    REFERENCES users(telegram_id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                reward INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS user_tasks (
                telegram_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (telegram_id, task_id),
                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id),
                FOREIGN KEY (task_id)
                    REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id)
                    REFERENCES users(telegram_id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_referred_by
            ON users(referred_by);

            CREATE INDEX IF NOT EXISTS idx_transactions_user
            ON transactions(telegram_id);
        """)

        default_tasks = [
            ("First Tap", 50),
            ("Tap 100 Times", 100),
            ("Earn 500 Points", 150),
            ("Visit Profile", 50),
            ("Explore Referrals", 50),
            ("Explore Missions", 50),
        ]

        for title, reward in default_tasks:
            conn.execute(
                """
                INSERT INTO tasks (title, reward)
                SELECT ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM tasks WHERE title = ?
                )
                """,
                (title, reward, title),
            )


if __name__ == "__main__":
    init_db()
    print("NOVYX database initialized successfully!")
