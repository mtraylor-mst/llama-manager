"""Tests for services/vram_stress_test.py."""

from unittest.mock import patch, MagicMock


class TestBuildCommandWithCtx:
    @patch("services.command_builder.build_command")
    def test_replaces_existing_ctx_size(self, mock_build):
        from services.vram_stress_test import _build_command_with_ctx

        mock_build.return_value = [
            "llama-server", "-m", "/model.gguf", "-c", "4096", "--threads", "8"
        ]
        args = _build_command_with_ctx(1, 8192)

        assert "-c" in args
        idx = args.index("-c")
        assert args[idx + 1] == "8192"

    @patch("services.command_builder.build_command")
    def test_appends_ctx_size_when_missing(self, mock_build):
        from services.vram_stress_test import _build_command_with_ctx

        mock_build.return_value = ["llama-server", "-m", "/model.gguf"]
        args = _build_command_with_ctx(1, 4096)

        assert "-c" in args
        idx = args.index("-c")
        assert args[idx + 1] == "4096"


class TestDeriveMetrics:
    def test_linear_regression_basic(self):
        from services.vram_stress_test import _derive_metrics

        # Simple linear relationship: 8GB base + 0.125 MB per token
        data_points = [
            {"ctx_tokens": 1024, "vram_used_mb": 8192, "peak_vram_mb": 8500},
            {"ctx_tokens": 2048, "vram_used_mb": 8400, "peak_vram_mb": 8700},
            {"ctx_tokens": 4096, "vram_used_mb": 8816, "peak_vram_mb": 9200},
        ]

        compaction, kv_per_token = _derive_metrics(data_points)

        assert kv_per_token is not None
        # Slope should be approximately 0.203 MB/token * 1048576 = ~213595 bytes/token
        assert kv_per_token > 0
        assert compaction is not None
        assert compaction >= 0

    def test_single_data_point(self):
        from services.vram_stress_test import _derive_metrics

        data_points = [
            {"ctx_tokens": 1024, "vram_used_mb": 8192, "peak_vram_mb": 8500},
        ]

        compaction, kv_per_token = _derive_metrics(data_points)

        # With single point, can't do regression
        assert kv_per_token is None
        # Compaction from single step: 8500/8192 - 1 = 0.0376 (rounded to 4 dp)
        assert compaction == 0.0376

    def test_empty_data_points(self):
        from services.vram_stress_test import _derive_metrics

        compaction, kv_per_token = _derive_metrics([])
        assert compaction is None
        assert kv_per_token is None

    def test_compaction_coefficient_calculation(self):
        from services.vram_stress_test import _derive_metrics

        data_points = [
            {"ctx_tokens": 1024, "vram_used_mb": 8000, "peak_vram_mb": 9600},
            {"ctx_tokens": 2048, "vram_used_mb": 8500, "peak_vram_mb": 9350},
        ]

        compaction, _ = _derive_metrics(data_points)

        # Step 1: 9600/8000 - 1 = 0.2
        # Step 2: 9350/8500 - 1 = 0.1
        # Max = 0.2
        assert compaction == 0.2


class TestRunStressTestConcurrency:
    @patch("services.vram_stress_test.get_conn")
    def test_rejects_concurrent_tests(self, mock_get_conn):
        from services.vram_stress_test import run_stress_test, _active_tests

        # Simulate an active test
        fake_thread = MagicMock()
        fake_thread.is_alive.return_value = True
        _active_tests[999] = fake_thread

        result = run_stress_test(1)

        assert "error" in result
        assert result["running_test_id"] == 999

        # Cleanup
        del _active_tests[999]

    @patch("services.vram_stress_test.VramMonitor.get_total_vram")
    @patch("services.vram_stress_test.get_conn")
    def test_creates_db_record(self, mock_get_conn, mock_total):
        from services.vram_stress_test import run_stress_test

        mock_total.return_value = 24576
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        with patch("services.vram_stress_test.threading.Thread"):
            result = run_stress_test(1)

            assert result["test_id"] == 42
            mock_cursor.execute.assert_called()


class TestGetStressTestStatus:
    @patch("services.vram_stress_test.get_conn")
    def test_returns_status_with_data_points(self, mock_get_conn):
        from services.vram_stress_test import get_stress_test_status

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {
                "id": 1,
                "version_id": 42,
                "status": "completed",
                "started_at": "2025-01-01 00:00:00",
                "completed_at": "2025-01-01 00:05:00",
                "total_vram_mb": 24576,
                "model_weight_size_mb": 16384,
                "compaction_coefficient": 0.05,
                "kv_per_token_bytes": 131072,
                "failure_ctx_tokens": None,
            },
        ]
        mock_cursor.fetchall.return_value = [
            {"ctx_tokens": 1024, "vram_used_mb": 8192, "peak_vram_mb": 8500, "tps": 50.0},
            {"ctx_tokens": 2048, "vram_used_mb": 8400, "peak_vram_mb": 8700, "tps": 48.0},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_stress_test_status(1)

        assert result is not None
        assert result["status"] == "completed"
        assert result["total_steps"] == 2
        assert result["compaction_coefficient"] == 0.05

    @patch("services.vram_stress_test.get_conn")
    def test_returns_none_for_missing_test(self, mock_get_conn):
        from services.vram_stress_test import get_stress_test_status

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_stress_test_status(999)
        assert result is None


class TestGetLatestStressTest:
    @patch("services.vram_stress_test.get_conn")
    def test_returns_latest_test(self, mock_get_conn):
        from services.vram_stress_test import get_latest_stress_test

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 5}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        with patch("services.vram_stress_test.get_stress_test_status") as mock_status:
            mock_status.return_value = {"id": 5, "status": "completed"}
            result = get_latest_stress_test(42)

            assert result is not None
            assert result["id"] == 5

    @patch("services.vram_stress_test.get_conn")
    def test_returns_none_when_no_tests(self, mock_get_conn):
        from services.vram_stress_test import get_latest_stress_test

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_latest_stress_test(42)
        assert result is None


class TestCancelStressTest:
    @patch("services.vram_stress_test._active_tests")
    def test_cancel_running_test(self, mock_active):
        from services.vram_stress_test import cancel_stress_test

        fake_thread = MagicMock()
        fake_thread.is_alive.return_value = True
        mock_active.get.return_value = fake_thread

        with patch("services.screen_manager.stop"):
            with patch("services.vram_stress_test._finish_test"):
                result = cancel_stress_test(1)
                assert result is True

    @patch("services.vram_stress_test._active_tests")
    def test_cancel_nonexistent_test(self, mock_active):
        from services.vram_stress_test import cancel_stress_test

        mock_active.get.return_value = None
        result = cancel_stress_test(999)
        assert result is False


class TestEnsureWikitext:
    @patch("services.vram_stress_test.os.path.exists")
    def test_returns_existing_file(self, mock_exists):
        from services.vram_stress_test import _ensure_wikitext

        mock_exists.return_value = True
        # Should return path without downloading
        result = _ensure_wikitext()
        assert result.endswith("wikitext.txt")


class TestServerHelpers:
    def test_get_server_url_defaults(self):
        from services.vram_stress_test import _get_server_url

        url = _get_server_url({"server": {}})
        assert url == "http://127.0.0.1:8080"

    def test_get_server_url_custom(self):
        from services.vram_stress_test import _get_server_url

        url = _get_server_url({"server": {"host": "0.0.0.0", "port": 9000}})
        assert url == "http://0.0.0.0:9000"
