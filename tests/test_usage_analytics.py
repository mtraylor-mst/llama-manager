"""Tests for models/usage.py and usage analytics endpoints."""

from unittest.mock import patch, MagicMock


class MockDictRow(dict):
    """A dict that also supports attribute access like DB rows."""
    def __getitem__(self, key):
        return super().get(key)


class TestRecordLaunch:
    @patch("models.usage.get_conn")
    def test_record_launch(self, mock_get_conn):
        from models.usage import record_launch

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.lastrowid = 5
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = record_launch(42)
        assert result == 5
        args = mock_cur.execute.call_args
        assert args[0][1] == (42,)


class TestRecordStop:
    @patch("models.usage.get_conn")
    def test_record_stop_found(self, mock_get_conn):
        from models.usage import record_stop

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = MockDictRow({"id": 5})
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = record_stop(exit_reason="user_stopped")
        assert result is True
        # Should have done SELECT then UPDATE
        assert mock_cur.execute.call_count == 2

    @patch("models.usage.get_conn")
    def test_record_stop_none_found(self, mock_get_conn):
        from models.usage import record_stop

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = record_stop(exit_reason="user_stopped")
        assert result is False
        # Should have done SELECT only
        assert mock_cur.execute.call_count == 1


class TestGetUsageStats:
    @patch("models.usage.get_conn")
    def test_get_usage_stats(self, mock_get_conn):
        from models.usage import get_usage_stats

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.side_effect = [
            [MockDictRow({
                "config_id": 1, "config_name": "Test Config",
                "total_launches": 5, "unique_versions": 2,
                "avg_runtime_sec": 3600.5, "last_launched_at": None,
            })],
            [MockDictRow({
                "config_id": 1, "exit_reason": "user_stopped", "cnt": 3,
            })],
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_usage_stats()
        assert len(result) == 1
        assert result[0]["config_name"] == "Test Config"
        assert result[0]["total_launches"] == 5
        assert result[0]["avg_runtime_sec"] == 3600
        assert result[0]["exit_reasons"]["user_stopped"] == 3

    @patch("models.usage.get_conn")
    def test_get_usage_stats_empty(self, mock_get_conn):
        from models.usage import get_usage_stats

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_usage_stats()
        assert result == []


class TestGetRecentSessions:
    @patch("models.usage.get_conn")
    def test_get_recent_sessions(self, mock_get_conn):
        from models.usage import get_recent_sessions

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            MockDictRow({
                "id": 1, "version_id": 42, "config_id": 1,
                "config_name": "Test", "version_number": 3,
                "launched_at": None, "stopped_at": None, "exit_reason": "user_stopped",
            }),
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_recent_sessions(10)
        assert len(result) == 1
        assert result[0]["config_name"] == "Test"


class TestGetRunningSessionCount:
    @patch("models.usage.get_conn")
    def test_get_running_session_count(self, mock_get_conn):
        from models.usage import get_running_session_count

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = MockDictRow({"cnt": 2})
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_running_session_count()
        assert result == 2


class TestUsageAnalyticsPage:
    def test_page_loads(self, client, mock_screen_manager):
        with patch("models.usage.get_usage_stats") as mock_stats:
            mock_stats.return_value = []
            with patch("models.usage.get_recent_sessions") as mock_sessions:
                mock_sessions.return_value = []
                with patch("models.usage.get_running_session_count") as mock_count:
                    mock_count.return_value = 0
                    resp = client.get("/usage-analytics")
                    assert resp.status_code == 200
                    assert b"Usage Analytics" in resp.data

    def test_page_shows_stats(self, client, mock_screen_manager):
        with patch("models.usage.get_usage_stats") as mock_stats:
            mock_stats.return_value = [
                {
                    "config_id": 1, "config_name": "Test Config",
                    "total_launches": 10, "unique_versions": 3,
                    "avg_runtime_sec": 1800, "last_launched_at": None,
                    "exit_reasons": {"user_stopped": 8, "crash": 2},
                },
            ]
            with patch("models.usage.get_recent_sessions") as mock_sessions:
                mock_sessions.return_value = []
                with patch("models.usage.get_running_session_count") as mock_count:
                    mock_count.return_value = 0
                    resp = client.get("/usage-analytics")
                    assert resp.status_code == 200
                    assert b"Test Config" in resp.data
                    assert b"10" in resp.data

    def test_page_shows_sessions(self, client, mock_screen_manager):
        from datetime import datetime

        with patch("models.usage.get_usage_stats") as mock_stats:
            mock_stats.return_value = []
            with patch("models.usage.get_recent_sessions") as mock_sessions:
                mock_sessions.return_value = [
                    {
                        "id": 1, "version_id": 42, "config_id": 1,
                        "config_name": "Test", "version_number": 3,
                        "launched_at": datetime(2025, 1, 1, 10, 0),
                        "stopped_at": datetime(2025, 1, 1, 11, 0),
                        "exit_reason": "user_stopped",
                    },
                ]
                with patch("models.usage.get_running_session_count") as mock_count:
                    mock_count.return_value = 0
                    resp = client.get("/usage-analytics")
                    assert resp.status_code == 200
                    assert b"Test" in resp.data
                    assert b"user_stopped" in resp.data

    def test_page_shows_empty_state(self, client, mock_screen_manager):
        with patch("models.usage.get_usage_stats") as mock_stats:
            mock_stats.return_value = []
            with patch("models.usage.get_recent_sessions") as mock_sessions:
                mock_sessions.return_value = []
                with patch("models.usage.get_running_session_count") as mock_count:
                    mock_count.return_value = 0
                    resp = client.get("/usage-analytics")
                    assert b"No usage data yet" in resp.data


class TestLaunchTrackingInStartRoute:
    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    def test_start_records_launch(self, mock_rate, client):
        with patch("services.config_validator.validate") as mock_val:
            mock_val.return_value = ([], [])
            with patch("services.command_builder.build_command") as mock_cmd:
                mock_cmd.return_value = ["llama-server", "--model", "/test.gguf"]
                with patch("services.screen_manager.start") as mock_start:
                    mock_start.return_value = {"success": True, "message": "Started (PID 1234)"}
                    with patch("models.usage.record_launch") as mock_record:
                        resp = client.post("/server/start/42", headers={"HX-Request": "true"})
                        assert resp.status_code == 200
                        mock_record.assert_called_once_with(42)

    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    def test_start_no_record_on_failure(self, mock_rate, client):
        with patch("services.config_validator.validate") as mock_val:
            mock_val.return_value = ([], [])
            with patch("services.command_builder.build_command") as mock_cmd:
                mock_cmd.return_value = ["llama-server", "--model", "/test.gguf"]
                with patch("services.screen_manager.start") as mock_start:
                    mock_start.return_value = {"success": False, "message": "Failed"}
                    with patch("models.usage.record_launch") as mock_record:
                        resp = client.post("/server/start/42", headers={"HX-Request": "true"})
                        assert resp.status_code == 200
                        mock_record.assert_not_called()


class TestStopTrackingInStopRoute:
    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    def test_stop_records_session(self, mock_rate, client):
        with patch("services.screen_manager.stop") as mock_stop:
            mock_stop.return_value = {"success": True, "message": "Server stopped"}
            with patch("models.usage.record_stop") as mock_record:
                resp = client.post("/server/stop", headers={"HX-Request": "true"})
                assert resp.status_code == 200
                mock_record.assert_called_once_with(exit_reason="user_stopped")

    @patch("utils.rate_limit._limiter.is_allowed", return_value=(True, 0))
    def test_stop_no_record_on_failure(self, mock_rate, client):
        with patch("services.screen_manager.stop") as mock_stop:
            mock_stop.return_value = {"success": False, "message": "Failed"}
            with patch("models.usage.record_stop") as mock_record:
                resp = client.post("/server/stop", headers={"HX-Request": "true"})
                assert resp.status_code == 200
                mock_record.assert_not_called()
