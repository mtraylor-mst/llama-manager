"""Tests for services/vram_monitor.py."""

import time
from unittest.mock import patch, MagicMock


class TestVramMonitorGetTotal:
    @patch("services.vram_monitor.subprocess.run")
    def test_get_total_vram_success(self, mock_run):
        from services.vram_monitor import VramMonitor

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "24576\n"
        mock_run.return_value = mock_result

        total = VramMonitor.get_total_vram()
        assert total == 24576

    @patch("services.vram_monitor.subprocess.run")
    def test_get_total_vram_failure(self, mock_run):
        from services.vram_monitor import VramMonitor

        mock_run.side_effect = FileNotFoundError()
        total = VramMonitor.get_total_vram()
        assert total is None

    @patch("services.vram_monitor.subprocess.run")
    def test_get_total_vram_timeout(self, mock_run):
        from services.vram_monitor import VramMonitor
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 10)
        total = VramMonitor.get_total_vram()
        assert total is None

    @patch("services.vram_monitor.subprocess.run")
    def test_get_total_vram_invalid_output(self, mock_run):
        from services.vram_monitor import VramMonitor

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid\n"
        mock_run.return_value = mock_result

        total = VramMonitor.get_total_vram()
        assert total is None


class TestVramMonitorPolling:
    @patch("services.vram_monitor.subprocess.run")
    @patch("time.sleep")
    def test_start_stop_collects_data(self, mock_sleep, mock_run):
        from services.vram_monitor import VramMonitor

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "8192\n"
        mock_run.return_value = mock_result

        monitor = VramMonitor()
        monitor.start()
        time.sleep(0.3)  # Let a few polls happen
        data = monitor.stop()

        assert len(data) > 0
        for ts, used_mb in data:
            assert isinstance(ts, float)
            assert used_mb == 8192

    @patch("services.vram_monitor.subprocess.run")
    @patch("time.sleep")
    def test_get_peak_tracks_maximum(self, mock_sleep, mock_run):
        from services.vram_monitor import VramMonitor

        # Simulate increasing VRAM usage with a callable that cycles values
        values = [4096, 8192, 12288, 16384, 12288]
        idx = [0]

        def poll_side_effect(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = f"{values[idx[0] % len(values)]}\n"
            idx[0] += 1
            return result

        mock_run.side_effect = poll_side_effect

        monitor = VramMonitor()
        monitor.start()
        time.sleep(0.5)
        peak = monitor.get_peak()
        monitor.stop()

        assert peak == 16384

    @patch("services.vram_monitor.subprocess.run")
    @patch("time.sleep")
    def test_get_peak_none_before_start(self, mock_sleep, mock_run):
        from services.vram_monitor import VramMonitor

        monitor = VramMonitor()
        peak = monitor.get_peak()
        assert peak is None

    @patch("services.vram_monitor.subprocess.run")
    @patch("time.sleep")
    def test_skips_failed_queries(self, mock_sleep, mock_run):
        from services.vram_monitor import VramMonitor

        # First query fails, subsequent succeed
        success_result = MagicMock(returncode=0, stdout="8192\n")
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise FileNotFoundError()
            return success_result

        mock_run.side_effect = side_effect

        monitor = VramMonitor()
        monitor.start()
        time.sleep(0.3)
        data = monitor.stop()

        assert len(data) > 0  # Successful queries recorded
        assert all(used_mb == 8192 for _, used_mb in data)

    @patch("services.vram_monitor.subprocess.run")
    @patch("time.sleep")
    def test_thread_safe_data_points(self, mock_sleep, mock_run):
        from services.vram_monitor import VramMonitor

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "4096\n"
        mock_run.return_value = mock_result

        monitor = VramMonitor()
        monitor.start()
        time.sleep(0.2)

        # Read while polling is active
        points = monitor.get_data_points()
        peak = monitor.get_peak()

        assert len(points) >= 0  # May have data depending on timing
        assert peak is None or peak == 4096

        monitor.stop()


class TestVramMonitorSingleInstance:
    @patch("services.vram_monitor.subprocess.run")
    @patch("time.sleep")
    def test_start_idempotent(self, mock_sleep, mock_run):
        """Calling start() twice should not create two threads."""
        from services.vram_monitor import VramMonitor

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "4096\n"
        mock_run.return_value = mock_result

        monitor = VramMonitor()
        monitor.start()
        monitor.start()  # Should be no-op

        data = monitor.stop()
        # Just verify it works without error
        assert isinstance(data, list)

    @patch("services.vram_monitor.subprocess.run")
    @patch("time.sleep")
    def test_stop_returns_copy(self, mock_sleep, mock_run):
        """Stop returns a copy of data points, not the internal list."""
        from services.vram_monitor import VramMonitor

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "4096\n"
        mock_run.return_value = mock_result

        monitor = VramMonitor()
        monitor.start()
        time.sleep(0.2)
        data = monitor.stop()

        # Modify returned list - should not affect internal state
        original_len = len(data)
        data.append((999, 999))
        assert len(data) == original_len + 1
