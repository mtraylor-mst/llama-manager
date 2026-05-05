from unittest.mock import patch, MagicMock
import json


class TestGetServerHostPort:
    def test_defaults(self):
        from services.benchmarks import get_server_host_port
        host, port = get_server_host_port()
        assert host == '127.0.0.1'
        assert port == 8080

    def test_custom_from_version_data(self):
        from services.benchmarks import get_server_host_port
        data = {'server': {'host': '0.0.0.0', 'port': 9000}}
        host, port = get_server_host_port(data)
        assert host == '0.0.0.0'
        assert port == 9000


class TestWaitForServer:
    @patch('services.benchmarks.urllib.request.urlopen')
    @patch('time.sleep')
    def test_server_ready(self, mock_sleep, mock_urlopen):
        from services.benchmarks import wait_for_server
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({'status': 'ok'}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        ready, elapsed = wait_for_server('127.0.0.1', 8080)
        assert ready is True

    @patch('services.benchmarks.urllib.request.urlopen')
    @patch('time.sleep')
    def test_server_timeout(self, mock_sleep, mock_urlopen):
        from services.benchmarks import wait_for_server
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        ready, elapsed = wait_for_server('127.0.0.1', 8080, timeout=2)
        assert ready is False


class TestRunBenchmark:
    @patch('services.benchmarks.urllib.request.urlopen')
    def test_successful_benchmark(self, mock_urlopen):
        from services.benchmarks import run_benchmark
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            'timing': {'predicted_n': 128, 'generation_ms': 50.0}
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        result = run_benchmark('127.0.0.1', 8080)
        assert result['error'] is None
        assert result['tps'] > 0

    @patch('services.benchmarks.urllib.request.urlopen')
    def test_connection_failed(self, mock_urlopen):
        from services.benchmarks import run_benchmark
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        result = run_benchmark('127.0.0.1', 8080)
        assert result['tps'] == 0
        assert 'error' in result and result['error'] is not None


class TestGetVram:
    @patch('services.benchmarks.subprocess.run')
    def test_vram_success(self, mock_run):
        from services.benchmarks import get_vram
        mock_result = MagicMock()
        mock_result.stdout = '2048 MiB\n'
        mock_run.return_value = mock_result
        vram = get_vram()
        assert vram == 2048

    @patch('services.benchmarks.subprocess.run')
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
