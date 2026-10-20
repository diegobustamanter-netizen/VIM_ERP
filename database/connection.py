import sqlite3
from config import DB_NAME
from contextlib import contextmanager

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def conectar_db(dict_rows: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    if dict_rows:
        conn.row_factory = dict_factory
    return conn

@contextmanager
def session_db(dict_rows: bool = False):
    conn = conectar_db(dict_rows)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()