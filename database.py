import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'it_asset_maintenance.db'
SCHEMA_PATH = BASE_DIR / 'schema.sql'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db()
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit(); conn.close()

if __name__ == '__main__':
    init_db(); print(f'Initialized {DB_PATH}')
