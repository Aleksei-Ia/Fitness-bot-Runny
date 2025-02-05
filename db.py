import sqlite3
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            weight REAL,
            height REAL,
            age INTEGER,
            gender TEXT,
            activity_level TEXT,
            goal TEXT,
            city TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            calories REAL,
            grams REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            workout_type TEXT,
            duration_minutes REAL,
            calories_burned REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def get_user_data(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def create_or_update_user(user_id: int, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users WHERE user_id=?', (user_id,))
    existing = cur.fetchone()
    if existing:
        sets = []
        vals = []
        for k, v in kwargs.items():
            sets.append(f'{k}=?')
            vals.append(v)
        vals.append(user_id)
        sql = f"UPDATE users SET {','.join(sets)} WHERE user_id=?"
        cur.execute(sql, tuple(vals))
    else:
        cols = list(kwargs.keys())
        vals = list(kwargs.values())
        sql = f"INSERT INTO users (user_id, {','.join(cols)}) VALUES ({','.join(['?']*(len(cols)+1))})"
        cur.execute(sql, (user_id, *vals))
    conn.commit()
    conn.close()


def log_water(user_id: int, amount: float):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('INSERT INTO water_logs (user_id, amount) VALUES (?,?)', (user_id, amount))
    conn.commit()
    conn.close()


def log_food(user_id: int, product_name: str, calories: float, grams: float):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO food_logs (user_id, product_name, calories, grams) 
        VALUES (?,?,?,?)
    ''', (user_id, product_name, calories, grams))
    conn.commit()
    conn.close()


def log_workout(user_id: int, wtype: str, duration: float, burned: float):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO workout_logs (user_id, workout_type, duration_minutes, calories_burned)
        VALUES (?,?,?,?)
    ''', (user_id, wtype, duration, burned))
    conn.commit()
    conn.close()
