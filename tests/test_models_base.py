from unittest.mock import patch


class TestGetConn:
    @patch("models.base.pymysql.connect")
    def test_get_conn_returns_connection(self, mock_connect):
        from models.base import get_conn

        get_conn()
        mock_connect.assert_called_once()
        call_kwargs = mock_connect.call_args[1]
        assert "cursorclass" in call_kwargs

    @patch("models.base.pymysql.connect")
    @patch("models.base.DB_HOST", "testhost")
    @patch("models.base.DB_USER", "testuser")
    @patch("models.base.DB_PASS", "testpass")
    @patch("models.base.DB_NAME", "testdb")
    def test_get_conn_passes_config_values(self, mock_connect):
        from models.base import get_conn

        get_conn()
        call_kwargs = mock_connect.call_args[1]
        assert call_kwargs["host"] == "testhost"
        assert call_kwargs["user"] == "testuser"
        assert call_kwargs["password"] == "testpass"
        assert call_kwargs["database"] == "testdb"
