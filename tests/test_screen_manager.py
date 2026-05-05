from unittest.mock import patch, MagicMock
import os
import tempfile


class TestGetLogFile:
    def test_with_version_id(self):
        from services.screen_manager import get_log_file
        assert get_log_file(42) == '/tmp/llama-server-42.log'

    def test_without_version_id(self):
        from services.screen_manager import get_log_file
        assert get_log_file() == '/tmp/llama-server.log'


class TestPidFile:
    @patch('services.screen_manager._find_running')
    def test_get_status_running(self, mock_find):
        from services.screen_manager import get_status
        mock_find.return_value = (12345, 1)
        status = get_status()
        assert status['running'] is True
        assert status['state'] == 'running'

    @patch('services.screen_manager._find_running')
    def test_get_status_stopped(self, mock_find):
        from services.screen_manager import get_status
        mock_find.return_value = (None, None)
        status = get_status()
        assert status['running'] is False
        assert status['state'] == 'stopped'

    @patch('services.screen_manager._find_running')
    def test_is_running_true(self, mock_find):
        from services.screen_manager import is_running
        mock_find.return_value = (12345, 1)
        assert is_running() is True

    @patch('services.screen_manager._find_running')
    def test_is_running_false(self, mock_find):
        from services.screen_manager import is_running
        mock_find.return_value = (None, None)
        assert is_running() is False


class TestReadPid:
    @patch('os.path.exists')
    def test_no_pid_file(self, mock_exists):
        from services.screen_manager import _read_pid
        mock_exists.return_value = False
        pid, vid = _read_pid()
        assert pid is None
        assert vid is None

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists')
    def test_valid_pid_file(self, mock_exists, mock_open):
        from services.screen_manager import _read_pid
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = '12345\n1\n'
        mock_open.return_value.__enter__.return_value = mock_file
        with patch('os.kill'):
            pid, vid = _read_pid()
            assert pid == 12345
            assert vid == 1

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.exists')
    def test_process_not_running(self, mock_exists, mock_open):
        from services.screen_manager import _read_pid
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = '12345\n1\n'
        mock_open.return_value.__enter__.return_value = mock_file
        with patch('os.kill', side_effect=ProcessLookupError()):
            pid, vid = _read_pid()
            assert pid is None


class TestStop:
    @patch('services.screen_manager._find_running')
    def test_no_server_running(self, mock_find):
        from services.screen_manager import stop
        mock_find.return_value = (None, None)
        result = stop()
        assert result['success'] is True

    @patch('services.screen_manager._find_running')
    def test_successful_stop(self, mock_find):
        from services.screen_manager import stop
        mock_find.return_value = (12345, 1)
        kill_count = [0]
        def fake_kill(pid, sig):
            kill_count[0] += 1
            if kill_count[0] > 1:
                raise ProcessLookupError()
        with patch('os.kill', side_effect=fake_kill):
            result = stop()
        assert result['success'] is True


class TestStart:
    @patch('services.screen_manager.is_running')
    @patch('services.screen_manager.subprocess.Popen')
    def test_start_success(self, mock_popen, mock_is_running):
        from services.screen_manager import start
        mock_is_running.return_value = False
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc
        result = start(['llama-server', '-m', 'model.gguf'], version_id=1)
        assert result['success'] is True
        assert '99999' in result['message']

    @patch('services.screen_manager.is_running')
    @patch('services.screen_manager.subprocess.Popen')
    def test_start_failure(self, mock_popen, mock_is_running):
        from services.screen_manager import start
        mock_is_running.return_value = False
        mock_popen.side_effect = FileNotFoundError()
        result = start(['llama-server', '-m', 'model.gguf'], version_id=1)
        assert result['success'] is False


class TestGetRunningVersionId:
    @patch('services.screen_manager._find_running')
    def test_returns_version_id(self, mock_find):
        from services.screen_manager import get_running_version_id
        mock_find.return_value = (12345, 7)
        assert get_running_version_id() == 7

    @patch('services.screen_manager._find_running')
    def test_none_when_not_running(self, mock_find):
        from services.screen_manager import get_running_version_id
        mock_find.return_value = (None, None)
        assert get_running_version_id() is None
