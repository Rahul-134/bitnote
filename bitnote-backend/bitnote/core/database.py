import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "bitnote.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000;")
    return conn