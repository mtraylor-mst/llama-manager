from unittest.mock import MagicMock, mock_open, patch


class TestGetLogFile:
    def test_with_version_id(self):
        from services.screen_manager import get_log_file

        result = get_log_file(42)
        assert result == "/tmp/llama-server-42.log"

    def test_without_version_id(self):
        from services.screen_manager import get_log_file

        result = get_log_file()
        assert result == "/tmp/llama-server.log"


class TestWritePid:
    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_write_pid(self):
        from services.screen_manager import _write_pid

        with patch("builtins.open", mock_open()) as mock_file:
            _write_pid(1234, 5)
            mock_file.assert_called_once_with("/tmp/test-pid-file", "w")
            mock_file().write.assert_called_once_with("1234\n5")

    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_write_pid_no_version(self):
        from services.screen_manager import _write_pid

        with patch("builtins.open", mock_open()) as mock_file:
            _write_pid(1234)
            mock_file.assert_called_once_with("/tmp/test-pid-file", "w")
            mock_file().write.assert_called_once_with("1234\n")


class TestReadPid:
    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_read_pid_success(self):
        from services.screen_manager import _read_pid

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="1234\n5")):
                with patch(
                    "services.screen_manager._is_our_process", return_value=True
                ):
                    pid, vid = _read_pid()
                    assert pid == 1234
                    assert vid == 5

    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_read_pid_no_file(self):
        from services.screen_manager import _read_pid

        with patch("os.path.exists", return_value=False):
            pid, vid = _read_pid()
            assert pid is None
            assert vid is None

    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_read_pid_invalid_data(self):
        from services.screen_manager import _read_pid

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid")):
                pid, vid = _read_pid()
                assert pid is None
                assert vid is None

    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_read_pid_not_our_process(self):
        from services.screen_manager import _read_pid

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="1234\n5")):
                with patch(
                    "services.screen_manager._is_our_process", return_value=False
                ):
                    pid, vid = _read_pid()
                    assert pid is None
                    assert vid is None


class TestCleanupPid:
    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_cleanup_pid_exists(self):
        from services.screen_manager import _cleanup_pid

        with patch("os.remove") as mock_remove:
            _cleanup_pid()
            mock_remove.assert_called_once_with("/tmp/test-pid-file")

    @patch("services.screen_manager._PID_FILE", "/tmp/test-pid-file")
    def test_cleanup_pid_not_exists(self):
        from services.screen_manager import _cleanup_pid

        with patch("os.remove", side_effect=OSError):
            _cleanup_pid()


class TestIsOurProcess:
    def test_is_our_process_true(self):
        from services.screen_manager import _is_our_process

        mock_status = mock_open(read_data="Uid:   1000")
        mock_comm = mock_open(read_data="llama-server")

        def open_side_effect(path, *args, **kwargs):
            if "status" in path:
                return mock_status(*args, **kwargs)
            return mock_comm(*args, **kwargs)

        with patch("os.kill"):
            with patch("os.getuid", return_value=1000):
                with patch("builtins.open", side_effect=open_side_effect):
                    result = _is_our_process(1234)
                    assert result is True

    def test_is_our_process_not_found(self):
        from services.screen_manager import _is_our_process

        with patch("os.kill", side_effect=ProcessLookupError):
            result = _is_our_process(99999)
            assert result is False

    def test_is_our_process_wrong_uid(self):
        from services.screen_manager import _is_our_process

        with patch("os.kill"):
            with patch("os.getuid", return_value=1000):
                with patch("builtins.open") as mock_file:
                    mock_file.return_value.__enter__.return_value.readlines.return_value = [
                        "Uid:   2000"
                    ]
                    result = _is_our_process(1234)
                    assert result is False

    def test_is_our_process_wrong_command(self):
        from services.screen_manager import _is_our_process

        with patch("os.kill"):
            with patch("os.getuid", return_value=1000):
                with patch("builtins.open") as mock_file:
                    mock_file.return_value.__enter__.return_value.readlines.side_effect = [
                        iter(["Uid:   1000"]),
                        iter(["other-process"]),
                    ]
                    result = _is_our_process(1234)
                    assert result is False


class TestExtractVersionIdFromLog:
    def test_extract_with_version(self):
        from services.screen_manager import _extract_version_id_from_log

        result = _extract_version_id_from_log("/tmp/llama-server-42.log")
        assert result == 42

    def test_extract_without_version(self):
        from services.screen_manager import _extract_version_id_from_log

        result = _extract_version_id_from_log("/tmp/llama-server.log")
        assert result is None

    def test_extract_invalid_path(self):
        from services.screen_manager import _extract_version_id_from_log

        result = _extract_version_id_from_log("/tmp/other-file.log")
        assert result is None


class TestFindRunning:
    @patch("services.screen_manager._read_pid")
    def test_find_running_from_pid_file(self, mock_read):
        from services.screen_manager import _find_running

        mock_read.return_value = (1234, 5)
        pid, vid = _find_running()
        assert pid == 1234
        assert vid == 5
        mock_read.assert_called_once()

    @patch("services.screen_manager._read_pid")
    @patch("services.screen_manager._is_our_process")
    @patch("subprocess.run")
    @patch("glob.glob")
    def test_find_running_lsof_fallback(
        self, mock_glob, mock_run, mock_is_ours, mock_read
    ):
        from services.screen_manager import _find_running

        mock_read.return_value = (None, None)
        mock_glob.return_value = ["/tmp/llama-server-7.log"]
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "5678\n"
        mock_run.return_value = mock_result
        mock_is_ours.return_value = True

        pid, vid = _find_running()
        assert pid == 5678
        assert vid == 7

    @patch("services.screen_manager._read_pid")
    @patch("subprocess.run")
    @patch("glob.glob")
    def test_find_running_no_process(self, mock_glob, mock_run, mock_read):
        from services.screen_manager import _find_running

        mock_read.return_value = (None, None)
        mock_glob.return_value = []

        pid, vid = _find_running()
        assert pid is None
        assert vid is None


class TestGetRunningVersionId:
    @patch("services.screen_manager._find_running")
    def test_get_running_version_id(self, mock_find):
        from services.screen_manager import get_running_version_id

        mock_find.return_value = (1234, 5)
        result = get_running_version_id()
        assert result == 5


class TestIsRunning:
    @patch("services.screen_manager._find_running")
    def test_is_running_true(self, mock_find):
        from services.screen_manager import is_running

        mock_find.return_value = (1234, 5)
        result = is_running()
        assert result is True

    @patch("services.screen_manager._find_running")
    def test_is_running_false(self, mock_find):
        from services.screen_manager import is_running

        mock_find.return_value = (None, None)
        result = is_running()
        assert result is False


class TestGetStatus:
    @patch("services.screen_manager._find_running")
    def test_get_status_running(self, mock_find):
        from services.screen_manager import get_status

        mock_find.return_value = (1234, 5)
        result = get_status()
        assert result["running"] is True
        assert result["state"] == "running"
        assert "PID 1234" in result["name"]

    @patch("services.screen_manager._find_running")
    def test_get_status_stopped(self, mock_find):
        from services.screen_manager import get_status

        mock_find.return_value = (None, None)
        result = get_status()
        assert result["running"] is False
        assert result["state"] == "stopped"


class TestStop:
    @patch("services.screen_manager._find_running")
    def test_stop_no_server(self, mock_find):
        from services.screen_manager import stop

        mock_find.return_value = (None, None)
        result = stop()
        assert result["success"] is True
        assert "No server running" in result["message"]

    @patch("services.screen_manager._find_running")
    def test_stop_success(self, mock_find):
        from services.screen_manager import stop

        mock_find.return_value = (1234, 5)
        with patch("os.kill") as mock_kill:
            mock_kill.side_effect = [None, ProcessLookupError()]
            with patch("time.sleep"):
                result = stop()
                assert result["success"] is True
                mock_kill.assert_called()


class TestStart:
    @patch("services.screen_manager.is_running")
    def test_start_success(self, mock_is_running):
        from services.screen_manager import start

        mock_is_running.return_value = False
        mock_proc = MagicMock()
        mock_proc.pid = 1234

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("builtins.open", mock_open()):
                with patch("services.screen_manager._write_pid"):
                    result = start(["llama-server", "-m", "model.bin"], version_id=1)
                    assert result["success"] is True
                    assert "PID 1234" in result["message"]
                    mock_popen.assert_called_once()

    @patch("services.screen_manager.is_running")
    def test_start_failure(self, mock_is_running):
        from services.screen_manager import start

        mock_is_running.return_value = False

        with patch("subprocess.Popen", side_effect=Exception("Failed")):
            result = start(["llama-server", "-m", "model.bin"], version_id=1)
            assert result["success"] is False
            assert "Failed to start" in result["message"]


class TestGetLogs:
    @patch("services.screen_manager._find_running")
    def test_get_logs_no_server(self, mock_find):
        from services.screen_manager import get_logs

        mock_find.return_value = (None, None)
        result = get_logs()
        assert result == ""

    @patch("services.screen_manager._find_running")
    def test_get_logs_success(self, mock_find):
        from services.screen_manager import get_logs

        mock_find.return_value = (1234, 5)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "log line 1\nlog line 2\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = get_logs(lines=10)
            assert result == "log line 1\nlog line 2\n"
            mock_run.assert_called_once()
            assert "-n" in mock_run.call_args[0][0]
            assert "10" in mock_run.call_args[0][0]
