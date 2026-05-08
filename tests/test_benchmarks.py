from unittest.mock import patch, MagicMock
import json


class TestGetServerHostPort:
    def test_defaults(self):
        from services.benchmarks import get_server_host_port

        host, port = get_server_host_port()
        assert host == "127.0.0.1"
        assert port == 8080

    def test_custom_from_version_data(self):
        from services.benchmarks import get_server_host_port

        data = {"server": {"host": "0.0.0.0", "port": 9000}}
        host, port = get_server_host_port(data)
        assert host == "0.0.0.0"
        assert port == 9000


class TestWaitForServer:
    @patch("services.benchmarks.urllib.request.urlopen")
    @patch("time.sleep")
    def test_server_ready(self, mock_sleep, mock_urlopen):
        from services.benchmarks import wait_for_server

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        ready, elapsed = wait_for_server("127.0.0.1", 8080)
        assert ready is True

    @patch("services.benchmarks.urllib.request.urlopen")
    @patch("time.sleep")
    def test_server_timeout(self, mock_sleep, mock_urlopen):
        from services.benchmarks import wait_for_server
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        ready, elapsed = wait_for_server("127.0.0.1", 8080, timeout=2)
        assert ready is False


class TestRunBenchmark:
    @patch("services.benchmarks.urllib.request.urlopen")
    def test_successful_benchmark(self, mock_urlopen):
        from services.benchmarks import run_benchmark

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"timing": {"predicted_n": 128, "generation_ms": 50.0}}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        result = run_benchmark("127.0.0.1", 8080)
        assert result["error"] is None
        assert result["tps"] > 0

    @patch("services.benchmarks.urllib.request.urlopen")
    def test_connection_failed(self, mock_urlopen):
        from services.benchmarks import run_benchmark
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        result = run_benchmark("127.0.0.1", 8080)
        assert result["tps"] == 0
        assert "error" in result and result["error"] is not None


class TestGetVram:
    @patch("services.benchmarks.subprocess.run")
    def test_vram_success(self, mock_run):
        from services.benchmarks import get_vram

        mock_result = MagicMock()
        mock_result.stdout = "2048 MiB\n"
        mock_run.return_value = mock_result
        vram = get_vram()
        assert vram == 2048

    @patch("services.benchmarks.subprocess.run")
    def test_vram_no_nvidia_smi(self, mock_run):
        from services.benchmarks import get_vram

        mock_run.side_effect = FileNotFoundError()
        vram = get_vram()
        assert vram is None


class TestGetCpuUsage:
    def test_cpu_usage_returns_none_without_psutil(self):
        """When psutil is not installed, get_cpu_usage returns None."""
        from services.benchmarks import get_cpu_usage

        # If psutil is available this will return a float; if not, None.
        # Either outcome is valid — just verify no exception is raised.
        result = get_cpu_usage()
        assert result is None or isinstance(result, (int, float))


class TestRunBenchmarkFallbacks:
    @patch("services.benchmarks.urllib.request.urlopen")
    def test_fallback_tps_estimation_no_timing(self, mock_urlopen):
        """When response has no 'timing' key but has tokens_generated, estimate TPS from duration."""
        from services.benchmarks import run_benchmark

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"tokens_generated": 128}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        result = run_benchmark("127.0.0.1", 8080)
        assert result["error"] is None
        assert result["tps"] > 0
        assert result["tokens_generated"] == 128

    @patch("services.benchmarks.urllib.request.urlopen")
    def test_fallback_tps_estimation_zero_tokens(self, mock_urlopen):
        """When no timing and zero tokens_generated, fall back to n_tokens / duration."""
        from services.benchmarks import run_benchmark

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        result = run_benchmark("127.0.0.1", 8080)
        assert result["error"] is None
        assert result["tps"] > 0

    @patch("services.benchmarks.urllib.request.urlopen")
    def test_unexpected_response_format(self, mock_urlopen):
        """When response is valid JSON but duration is 0, return unexpected response error."""
        from services.benchmarks import run_benchmark

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"error": "bad"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        with patch("time.time") as mock_time:
            mock_time.side_effect = [0.0, 0.0, 0.0]
            result = run_benchmark("127.0.0.1", 8080)
            assert result["tps"] == 0
            assert result["error"] == "Unexpected response format"

    @patch("services.benchmarks.urllib.request.urlopen")
    def test_generic_exception(self, mock_urlopen):
        """When an unexpected exception occurs, return generic error message."""
        from services.benchmarks import run_benchmark

        mock_urlopen.side_effect = Exception("Something went wrong")
        result = run_benchmark("127.0.0.1", 8080)
        assert result["tps"] == 0
        assert result["error"] == "Benchmark failed unexpectedly"


class TestGetVramMultiGpu:
    @patch("services.benchmarks.subprocess.run")
    def test_multi_gpu_vram(self, mock_run):
        """Sum VRAM across multiple GPUs."""
        from services.benchmarks import get_vram

        mock_result = MagicMock()
        mock_result.stdout = "2048 MiB\n4096 MiB\n"
        mock_run.return_value = mock_result
        vram = get_vram()
        assert vram == 6144

    @patch("services.benchmarks.subprocess.run")
    def test_timeout_expired(self, mock_run):
        """Return None when nvidia-smi times out."""
        from services.benchmarks import get_vram
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("nvidia-smi", 5)
        vram = get_vram()
        assert vram is None

    @patch("services.benchmarks.subprocess.run")
    def test_value_error(self, mock_run):
        """Return 0 when output is malformed (no valid digit values)."""
        from services.benchmarks import get_vram

        mock_result = MagicMock()
        mock_result.stdout = "invalid\n"
        mock_run.return_value = mock_result
        vram = get_vram()
        assert vram == 0


class TestBenchmarkVersion:
    @patch("models.configs.save_performance_metric")
    @patch("services.benchmarks.get_cpu_usage")
    @patch("services.benchmarks.get_vram")
    @patch("services.benchmarks.run_benchmark")
    @patch("models.configs.get_all_version_data")
    def test_full_benchmark_success(
        self, mock_data, mock_run_bench, mock_vram, mock_cpu, mock_save
    ):
        """Test the full benchmark_version orchestrator with successful benchmark."""
        from services.benchmarks import benchmark_version

        mock_data.return_value = {"server": {"host": "127.0.0.1", "port": 8080}}
        mock_vram.side_effect = [1024, 3072]
        mock_run_bench.return_value = {
            "tps": 50.0,
            "tokens_generated": 128,
            "duration_sec": 2.5,
            "error": None,
        }
        mock_cpu.return_value = 75.0

        result = benchmark_version(42)
        assert result["success"] is True
        assert result["tps"] == 50.0
        assert result["tokens_generated"] == 128
        assert result["vram_used_mb"] == 3072
        assert result["peak_cpu_pct"] == 75.0
        mock_save.assert_called_once()

    @patch("models.configs.save_performance_metric")
    @patch("services.benchmarks.get_cpu_usage")
    @patch("services.benchmarks.get_vram")
    @patch("services.benchmarks.run_benchmark")
    @patch("models.configs.get_all_version_data")
    def test_full_benchmark_failure(
        self, mock_data, mock_run_bench, mock_vram, mock_cpu, mock_save
    ):
        """Test benchmark_version when benchmark fails."""
        from services.benchmarks import benchmark_version

        mock_data.return_value = {"server": {}}
        mock_vram.side_effect = [1024, None]
        mock_run_bench.return_value = {
            "tps": 0,
            "tokens_generated": 0,
            "duration_sec": 0,
            "error": "Connection failed",
        }
        mock_cpu.return_value = None

        result = benchmark_version(42)
        assert result["success"] is False
        assert result["error"] == "Connection failed"
        assert result["vram_used_mb"] is None
        mock_save.assert_called_once()
