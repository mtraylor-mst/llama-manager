import sys
import os
import pytest
from unittest.mock import patch

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockCursor:
    """Mock pymysql cursor that returns configurable results."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self.lastrowid = 1
        self.rowcount = 1

    def execute(self, sql, params=None):
        pass

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockConnection:
    """Mock pymysql connection."""

    def __init__(self, rows=None):
        self._rows = rows

    def cursor(self):
        return MockCursor(self._rows)

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture
def mock_db():
    """Patch models.base.get_conn to return a mock connection."""
    with patch('models.base.get_conn') as mock_conn:
        mock_conn.return_value = MockConnection()
        yield mock_conn
