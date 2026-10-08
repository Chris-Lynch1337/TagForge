"""Database connection helpers for TagForge."""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / 'tagforge.db'


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    """Open the database with named rows and foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn