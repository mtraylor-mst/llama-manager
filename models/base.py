"""Thread-safe database connection pool."""

import threading
from queue import Queue, Empty
import pymysql
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME

_MAX_CONNECTIONS = 10
_pool = None
_pool_lock = threading.Lock()


def _create_conn():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _get_pool():
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = Queue(maxsize=_MAX_CONNECTIONS)
    return _pool


class PooledConnection:
    """Wrapper that returns connections to the pool on context exit."""

    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def cursor(self, *args, **kwargs):
        cur = self._conn.cursor(*args, **kwargs)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        release_conn(self._conn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()
        return False


def get_conn():
    """Get a connection from the pool, creating one if necessary."""
    pool = _get_pool()
    try:
        raw = pool.get_nowait()
    except Empty:
        if pool.qsize() < _MAX_CONNECTIONS:
            raw = _create_conn()
        else:
            raw = pool.get(timeout=10)
    return PooledConnection(raw)


def release_conn(conn):
    """Return a raw pymysql connection to the pool."""
    pool = _get_pool()
    try:
        conn.ping(reconnect=False)
        pool.put_nowait(conn)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        if pool.qsize() < _MAX_CONNECTIONS:
            try:
                pool.put_nowait(_create_conn())
            except Exception:
                pass
