# src/api/db.py
"""Database connection module for the API."""

import os
import psycopg2
from psycopg2 import pool
from typing import Optional
from contextlib import contextmanager

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Connection pool
_connection_pool: Optional[pool.ThreadedConnectionPool] = None

def get_connection_pool():
    """Get or create the connection pool."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    return _connection_pool

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        pool = get_connection_pool()
        conn = pool.getconn()
        yield conn
    finally:
        if conn:
            pool.putconn(conn)

@contextmanager
def get_db_cursor():
    """Context manager for database cursors."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
