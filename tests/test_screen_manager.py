from unittest.mock import patch, MagicMock


def _mock_open_factory(contents_dict):
    """Create a mock open that returns different content based on path."""

    def mock_open(path, *args, **kwargs):
        content = contents_dict.get(path, "")
        # Split preserving newlines for readlines()
        raw_lines = content.splitlines(keepends=True) if content else []
        mock_file = MagicMock()
        mock_file.read.return_value = content
        mock_file.readlines.return_value = raw_lines
        mock_file.__enter__ = lambda self: mock_file
        mock_file.__exit__ = lambda self, *a: None
        return mock_file

    return mock_open


class TestIsOurProcess:
    @patch("os.getuid")
    @patch("os.kill")
    def test_valid_process(self, mock_kill, mock_getuid):
        from services.screen_manager import _is_our_process

        mock_kill.side_effect = None
        mock_getuid.return_value = 1000

        contents = {
            "/proc/12345/status": "Uid:\t1000\t1000\t1000\t1000\n",
            "/proc/12345/comm": "llama-server\n",
        }
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = _mock_open_factory(contents)
            assert _is_our_process(12345) is True

    @patch("os.getuid")
    @patch("os.kill")
    def test_wrong_uid(self, mock_kill, mock_getuid):
        from services.screen_manager import _is_our_process

        mock_kill.side_effect = None
        mock_getuid.return_value = 1000

        contents = {
            "/proc/12345/status": "Uid:\t9999\t9999\t9999\t9999\n",
        }
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = _mock_open_factory(contents)
            assert _is_our_process(12345) is False

    @patch("os.getuid")
    @patch("os.kill")
    def test_not_llama_server(self, mock_kill, mock_getuid):
        from services.screen_manager import _is_our_process

        mock_kill.side_effect = None
        mock_getuid.return_value = 1000

        contents = {
            "/proc/12345/status": "Uid:\t1000\t1000\t1000\t1000\n",
            "/proc/12345/comm": "bash\n",
        }
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = _mock_open_factory(contents)
            assert _is_our_process(12345) is False

    @patch("os.kill")
    def test_process_not_running(self, mock_kill):
        from services.screen_manager import _is_our_process

        mock_kill.side_effect = ProcessLookupError()
        assert _is_our_process(99999) is False

    @patch("os.kill")
    def test_permission_denied(self, mock_kill):
        from services.screen_manager import _is_our_process

        mock_kill.side_effect = PermissionError()
        assert _is_our_process(99999) is False


class TestExtractVersionIdFromLog:
    def test_with_version_id(self):
        from services.screen_manager import _extract_version_id_from_log

        assert _extract_version_id_from_log("/tmp/llama-server-42.log") == 42

    def test_without_version_id(self):
        from services.screen_manager import _extract_version_id_from_log

        assert _extract_version_id_from_log("/tmp/llama-server.log") is None

    def test_non_numeric_suffix(self):
        from services.screen_manager import _extract_version_id_from_log

        assert _extract_version_id_from_log("/tmp/llama-server-abc.log") is None


class TestGetLogFile:
    def test_with_version_id(self):
        from services.screen_manager import get_log_file

        assert get_log_file(42) == "/tmp/llama-server-42.log"

    def test_without_version_id(self):
        from services.screen_manager import get_log_file

        assert get_log_file() == "/tmp/llama-server.log"


class TestPidFile:
    @patch("services.screen_manager._find_running")
    def test_get_status_running(self, mock_find):
        from services.screen_manager import get_status

        mock_find.return_value = (12345, 1)
        status = get_status()
        assert status["running"] is True
        assert status["state"] == "running"

    @patch("services.screen_manager._find_running")
    def test_get_status_stopped(self, mock_find):
        from services.screen_manager import get_status

        mock_find.return_value = (None, None)
        status = get_status()
        assert status["running"] is False
        assert status["state"] == "stopped"

    @patch("services.screen_manager._find_running")
    def test_is_running_true(self, mock_find):
        from services.screen_manager import is_running

        mock_find.return_value = (12345, 1)
        assert is_running() is True

    @patch("services.screen_manager._find_running")
    def test_is_running_false(self, mock_find):
        from services.screen_manager import is_running

        mock_find.return_value = (None, None)
        assert is_running() is False


class TestReadPid:
    @patch("os.path.exists")
    def test_no_pid_file(self, mock_exists):
        from services.screen_manager import _read_pid

        mock_exists.return_value = False
        pid, vid = _read_pid()
        assert pid is None
        assert vid is None

    @patch("services.screen_manager._is_our_process")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.path.exists")
    def test_valid_pid_file(self, mock_exists, mock_open, mock_is_our):
        from services.screen_manager import _read_pid

        mock_exists.return_value = True
        mock_is_our.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "12345\n1\n"
        mock_open.return_value.__enter__.return_value = mock_file
        pid, vid = _read_pid()
        assert pid == 12345
        assert vid == 1

    @patch("builtins.open", new_callable=MagicMock)
    @patch("os.path.exists")
    def test_process_not_running(self, mock_exists, mock_open):
        from services.screen_manager import _read_pid

        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "12345\n1\n"
        mock_open.return_value.__enter__.return_value = mock_file
        with patch("os.kill", side_effect=ProcessLookupError()):
            pid, vid = _read_pid()
            assert pid is None


class TestStop:
    @patch("services.screen_manager._find_running")
    def test_no_server_running(self, mock_find):
        from services.screen_manager import stop

        mock_find.return_value = (None, None)
        result = stop()
        assert result["success"] is True

    @patch("services.screen_manager._find_running")
    def test_successful_stop(self, mock_find):
        from services.screen_manager import stop

        mock_find.return_value = (12345, 1)
        kill_count = [0]

        def fake_kill(pid, sig):
            kill_count[0] += 1
            if kill_count[0] > 1:
                raise ProcessLookupError()

        with patch("os.kill", side_effect=fake_kill):
            result = stop()
        assert result["success"] is True


class TestStart:
    @patch("services.screen_manager.is_running")
    @patch("services.screen_manager.subprocess.Popen")
    def test_start_success(self, mock_popen, mock_is_running):
        from services.screen_manager import start

        mock_is_running.return_value = False
        mock_proc = MagicMock()
        mock_proc.pid = 99999
        mock_popen.return_value = mock_proc
        result = start(["llama-server", "-m", "model.gguf"], version_id=1)
        assert result["success"] is True
        assert "99999" in result["message"]

    @patch("services.screen_manager.is_running")
    @patch("services.screen_manager.subprocess.Popen")
    def test_start_failure(self, mock_popen, mock_is_running):
        from services.screen_manager import start

        mock_is_running.return_value = False
        mock_popen.side_effect = FileNotFoundError()
        result = start(["llama-server", "-m", "model.gguf"], version_id=1)
        assert result["success"] is False


class TestGetRunningVersionId:
    @patch("services.screen_manager._find_running")
    def test_returns_version_id(self, mock_find):
        from services.screen_manager import get_running_version_id

        mock_find.return_value = (12345, 7)
        assert get_running_version_id() == 7

    @patch("services.screen_manager._find_running")
    def test_none_when_not_running(self, mock_find):
        from services.screen_manager import get_running_version_id

        mock_find.return_value = (None, None)
        assert get_running_version_id() is None
