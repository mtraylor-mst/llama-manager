import subprocess
from unittest.mock import patch, mock_open

from services.config_importer import (
    parse_args,
    coerce_value,
    _normalize_flag,
    _extract_model_name,
    get_server_pid,
    read_cmdline,
    _compare_signatures,
    import_running_config,
)


class TestNormalizeFlag:
    def test_strip_dashes(self):
        assert _normalize_flag("--threads") == "threads"

    def test_convert_underscores(self):
        assert _normalize_flag("--cache-type-k") == "cache-type-k"

    def test_single_dash(self):
        assert _normalize_flag("-m") == "m"


class TestParseArgs:
    def test_simple_long_flag_with_value(self):
        args = ["llama-server", "--threads", "8"]
        result = parse_args(args)
        assert result["threads"] == "8"

    def test_short_flag_with_value(self):
        args = ["llama-server", "-m", "/path/to/model.gguf"]
        result = parse_args(args)
        assert result["model"] == "/path/to/model.gguf"

    def test_boolean_flag(self):
        args = ["llama-server", "--mmap"]
        result = parse_args(args)
        assert result["mmap"] is True

    def test_negative_flag(self):
        args = ["llama-server", "--no-mmap"]
        result = parse_args(args)
        assert result["mmap"] is False

    def test_eq_format(self):
        args = ["llama-server", "--host=0.0.0.0"]
        result = parse_args(args)
        assert result["host"] == "0.0.0.0"

    def test_multiple_flags(self):
        args = ["llama-server", "-t", "8", "--mmap", "-c", "4096"]
        result = parse_args(args)
        assert result["threads"] == "8"
        assert result["mmap"] is True
        assert result["ctx-size"] == "4096"

    def test_empty_args(self):
        args = None
        result = parse_args(args)
        assert result == {}


class TestCoerceValue:
    def test_bool_true(self):
        assert coerce_value("mmap", True) == 1

    def test_bool_false(self):
        assert coerce_value("mmap", False) == 0

    def test_int_column(self):
        assert coerce_value("ctx_size", "4096") == 4096

    def test_float_column(self):
        assert coerce_value("temperature", "0.8") == 0.8

    def test_none_value(self):
        assert coerce_value("threads", None) is None

    def test_string_passthrough(self):
        result = coerce_value("model_path", "/path/to/model.gguf")
        assert result == "/path/to/model.gguf"


class TestExtractModelName:
    def test_from_model_path(self):
        parsed = {"model": "/home/user/models/mistral-7b.gguf"}
        assert _extract_model_name(parsed) == "mistral-7b.gguf"

    def test_from_hf_repo_and_file(self):
        parsed = {"hf-repo": "user/repo", "hf-file": "model.gguf"}
        assert _extract_model_name(parsed) == "user/repo/model.gguf"

    def test_from_hf_repo_only(self):
        parsed = {"hf-repo": "user/repo"}
        assert _extract_model_name(parsed) == "user/repo"

    def test_none_when_no_model_info(self):
        parsed = {}
        assert _extract_model_name(parsed) is None


class TestGetServerPid:
    def test_returns_pid_when_running(self):
        with patch("services.config_importer.get_status") as mock_status:
            mock_status.return_value = {"running": True}
            with patch("subprocess.check_output", return_value="1234\n5678"):
                pid = get_server_pid()
                assert pid == 1234

    def test_returns_none_when_not_running(self):
        with patch("services.config_importer.get_status") as mock_status:
            mock_status.return_value = {"running": False}
            pid = get_server_pid()
            assert pid is None

    def test_returns_none_on_pgrep_error(self):
        with patch("services.config_importer.get_status") as mock_status:
            mock_status.return_value = {"running": True}
            with patch(
                "subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "pgrep"),
            ):
                pid = get_server_pid()
                assert pid is None

    def test_returns_none_on_empty_output(self):
        with patch("services.config_importer.get_status") as mock_status:
            mock_status.return_value = {"running": True}
            with patch("subprocess.check_output", return_value=""):
                pid = get_server_pid()
                assert pid is None


class TestReadCmdline:
    def test_reads_cmdline_success(self):
        cmdline = b"llama-server\x00-m\x00/model.gguf\x00-t\x008"
        with patch("builtins.open", mock_open(read_data=cmdline)):
            result = read_cmdline(1234)
            assert result == ["llama-server", "-m", "/model.gguf", "-t", "8"]

    def test_returns_none_on_file_not_found(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = read_cmdline(99999)
            assert result is None

    def test_returns_none_on_permission_error(self):
        with patch("builtins.open", side_effect=PermissionError):
            result = read_cmdline(99999)
            assert result is None


class TestCompareSignatures:
    @patch("models.configs.get_category")
    @patch("models.configs.CATEGORIES", ["model_loading", "context_batching"])
    def test_matching_signature(self, mock_get_category):
        mock_get_category.return_value = {
            "model_path": "/models/test.gguf",
            "ctx_size": 4096,
        }
        signature = {
            "model_path": "/models/test.gguf",
            "ctx_size": 4096,
        }
        result = _compare_signatures(signature, 1)
        assert result is True

    @patch("models.configs.get_category")
    @patch("models.configs.CATEGORIES", ["model_loading", "context_batching"])
    def test_non_matching_signature(self, mock_get_category):
        mock_get_category.return_value = {
            "model_path": "/models/other.gguf",
            "ctx_size": 2048,
        }
        signature = {
            "model_path": "/models/test.gguf",
            "ctx_size": 4096,
        }
        result = _compare_signatures(signature, 1)
        assert result is False

    @patch("models.configs.get_category")
    @patch("models.configs.CATEGORIES", ["model_loading", "context_batching"])
    def test_zero_values_are_compared(self, mock_get_category):
        mock_get_category.return_value = {
            "model_path": "/models/test.gguf",
            "ctx_size": 2048,
        }
        signature = {
            "model_path": "/models/test.gguf",
            "ctx_size": 0,
        }
        result = _compare_signatures(signature, 1)
        assert result is False

    @patch("models.configs.get_category")
    @patch("models.configs.CATEGORIES", ["model_loading"])
    def test_numeric_comparison(self, mock_get_category):
        mock_get_category.return_value = {
            "model_path": "/models/test.gguf",
        }
        signature = {
            "model_path": "/models/test.gguf",
        }
        result = _compare_signatures(signature, 1)
        assert result is True

    @patch("models.configs.get_category")
    @patch("models.configs.CATEGORIES", ["model_loading"])
    def test_zero_matches_zero(self, mock_get_category):
        mock_get_category.return_value = {
            "model_path": "/models/test.gguf",
            "ctx_size": 0,
        }
        signature = {
            "model_path": "/models/test.gguf",
            "ctx_size": 0,
        }
        result = _compare_signatures(signature, 1)
        assert result is True

    @patch("models.configs.get_category")
    @patch("models.configs.CATEGORIES", ["model_loading"])
    def test_none_and_empty_skipped(self, mock_get_category):
        mock_get_category.return_value = {
            "model_path": "/models/test.gguf",
        }
        signature = {
            "model_path": "/models/test.gguf",
            "some_field": None,
            "another_field": "",
        }
        result = _compare_signatures(signature, 1)
        assert result is True


class TestImportRunningConfig:
    @patch("models.configs.save_category")
    @patch("models.configs.create_version")
    @patch("models.configs.create_config")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_configs")
    @patch("services.config_importer._compare_signatures")
    @patch("services.config_importer.read_cmdline")
    @patch("services.config_importer.get_server_pid")
    def test_creates_new_config(
        self,
        mock_pid,
        mock_read,
        mock_compare,
        mock_configs,
        mock_latest,
        mock_create_cfg,
        mock_create_ver,
        mock_save_cat,
    ):
        mock_pid.return_value = 1234
        mock_read.return_value = ["llama-server", "-m", "/models/test.gguf", "-t", "8"]
        mock_configs.return_value = []
        mock_create_cfg.return_value = 10
        mock_create_ver.return_value = 20

        cfg_id, ver_id, parsed, created = import_running_config()
        assert cfg_id == 10
        assert ver_id == 20
        assert created is True
        assert parsed["model"] == "/models/test.gguf"
        mock_create_cfg.assert_called_once()
        mock_create_ver.assert_called_once()

    @patch("models.configs.save_category")
    @patch("models.configs.create_version")
    @patch("models.configs.create_config")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_configs")
    @patch("services.config_importer._compare_signatures")
    @patch("services.config_importer.read_cmdline")
    @patch("services.config_importer.get_server_pid")
    def test_existing_config_matches_no_new_version(
        self,
        mock_pid,
        mock_read,
        mock_compare,
        mock_configs,
        mock_latest,
        mock_create_cfg,
        mock_create_ver,
        mock_save_cat,
    ):
        mock_pid.return_value = 1234
        mock_read.return_value = ["llama-server", "-m", "/models/test.gguf", "-t", "8"]
        mock_configs.return_value = [{"id": 5, "name": "test.gguf"}]
        mock_latest.return_value = {"id": 15}
        mock_compare.return_value = True

        cfg_id, ver_id, parsed, created = import_running_config()
        assert cfg_id == 5
        assert ver_id == 15
        assert created is False
        mock_create_cfg.assert_not_called()
        mock_create_ver.assert_not_called()

    @patch("models.configs.save_category")
    @patch("models.configs.create_version")
    @patch("models.configs.create_config")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_configs")
    @patch("services.config_importer._compare_signatures")
    @patch("services.config_importer.read_cmdline")
    @patch("services.config_importer.get_server_pid")
    def test_existing_config_differs_creates_new_version(
        self,
        mock_pid,
        mock_read,
        mock_compare,
        mock_configs,
        mock_latest,
        mock_create_cfg,
        mock_create_ver,
        mock_save_cat,
    ):
        mock_pid.return_value = 1234
        mock_read.return_value = ["llama-server", "-m", "/models/test.gguf", "-t", "8"]
        mock_configs.return_value = [{"id": 5, "name": "test.gguf"}]
        mock_latest.return_value = {"id": 15}
        mock_compare.return_value = False
        mock_create_ver.return_value = 25

        cfg_id, ver_id, parsed, created = import_running_config()
        assert cfg_id == 5
        assert ver_id == 25
        assert created is True
        mock_create_cfg.assert_not_called()
        mock_create_ver.assert_called_once()

    @patch("services.config_importer.read_cmdline")
    @patch("services.config_importer.get_server_pid")
    def test_raises_when_no_pid(self, mock_pid, mock_read):
        mock_pid.return_value = None
        try:
            import_running_config()
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "No running llama-server" in str(e)

    @patch("services.config_importer.read_cmdline")
    @patch("services.config_importer.get_server_pid")
    def test_raises_when_cmdline_unreadable(self, mock_pid, mock_read):
        mock_pid.return_value = 1234
        mock_read.return_value = None
        try:
            import_running_config()
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "Could not read cmdline" in str(e)

    @patch("models.configs.save_category")
    @patch("models.configs.create_version")
    @patch("models.configs.create_config")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_configs")
    @patch("services.config_importer._compare_signatures")
    @patch("services.config_importer.read_cmdline")
    @patch("services.config_importer.get_server_pid")
    def test_uses_custom_config_name(
        self,
        mock_pid,
        mock_read,
        mock_compare,
        mock_configs,
        mock_latest,
        mock_create_cfg,
        mock_create_ver,
        mock_save_cat,
    ):
        mock_pid.return_value = 1234
        mock_read.return_value = ["llama-server", "-m", "/models/test.gguf"]
        mock_configs.return_value = []
        mock_create_cfg.return_value = 10
        mock_create_ver.return_value = 20

        import_running_config(config_name="My Custom Config")
        mock_create_cfg.assert_called_once()
        call_kwargs = mock_create_cfg.call_args
        assert call_kwargs[1]["name"] == "test.gguf"

    @patch("models.configs.save_category")
    @patch("models.configs.create_version")
    @patch("models.configs.create_config")
    @patch("models.configs.get_latest_version")
    @patch("models.configs.get_all_configs")
    @patch("services.config_importer._compare_signatures")
    @patch("services.config_importer.read_cmdline")
    @patch("services.config_importer.get_server_pid")
    def test_uses_default_name_when_no_model(
        self,
        mock_pid,
        mock_read,
        mock_compare,
        mock_configs,
        mock_latest,
        mock_create_cfg,
        mock_create_ver,
        mock_save_cat,
    ):
        mock_pid.return_value = 1234
        mock_read.return_value = ["llama-server", "-t", "8"]
        mock_configs.return_value = []
        mock_create_cfg.return_value = 10
        mock_create_ver.return_value = 20

        import_running_config()
        mock_create_cfg.assert_called_once()
        call_kwargs = mock_create_cfg.call_args
        assert call_kwargs[1]["name"] == "Imported Config"


class TestCoerceValueParseFailure:
    def test_coerce_int_failure_fallback(self):
        result = coerce_value("ctx_size", "abc")
        assert result == "abc"

    def test_coerce_float_failure_fallback(self):
        result = coerce_value("temperature", "hot")
        assert result == "hot"
