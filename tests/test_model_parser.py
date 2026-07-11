"""Tests for services/model_parser.py."""

from unittest.mock import patch, MagicMock


SAMPLE_LOG = """\
llama-server loaded
print_info: architecture          = Qwen2
print_info: n_ctx                 = 32768
print_info: n_layer               = 64
print_info: n_embd                = 5120
print_info: n_head                = 40
print_info: n_head_kv             = 8
print_info: n_ctx_train           = 32768
print_info: key_length            = 128
print_info: value_length          = 256
print_info: n_vocab               = 152064
file size   = 15.65 GiB (5.00 BPW)
common_memory_breakdown_print: | info | 24124 = 23259 + (20791 = 15345 +    4950 +     495) + remaining
"""

MINIMAL_LOG = """\
print_info: n_layer               = 32
print_info: n_embd                = 4096
print_info: n_head                = 32
print_info: n_head_kv             = 4
file size   = 4.50 GiB (3.52 BPW)
"""

NO_ARCH_LOG = """\
some random log line
no architecture info here
"""


class TestParseLog:
    def test_parse_full_log(self, tmp_path):
        from services.model_parser import parse_log

        log_file = tmp_path / "test.log"
        log_file.write_text(SAMPLE_LOG)

        result = parse_log(str(log_file))

        assert result is not None
        assert result["architecture"] == "Qwen2"
        assert result["n_layers"] == 64
        assert result["n_embd"] == 5120
        assert result["n_head"] == 40
        assert result["n_head_kv"] == 8
        assert result["n_ctx_train"] == 32768
        assert result["key_length"] == 128
        assert result["value_length"] == 256
        assert result["file_size_bytes"] == int(15.65 * (1024 ** 3))

    def test_parse_minimal_log(self, tmp_path):
        from services.model_parser import parse_log

        log_file = tmp_path / "test.log"
        log_file.write_text(MINIMAL_LOG)

        result = parse_log(str(log_file))

        assert result is not None
        assert result["n_layers"] == 32
        assert result["n_embd"] == 4096
        assert result["n_head_kv"] == 4
        assert result["n_ctx_train"] is None
        assert result["file_size_bytes"] == int(4.50 * (1024 ** 3))

    def test_parse_empty_log(self, tmp_path):
        from services.model_parser import parse_log

        log_file = tmp_path / "test.log"
        log_file.write_text("")

        result = parse_log(str(log_file))
        assert result is None

    def test_parse_nonexistent_file(self):
        from services.model_parser import parse_log

        result = parse_log("/nonexistent/path/to/log.log")
        assert result is None

    def test_parse_no_architecture_log(self, tmp_path):
        from services.model_parser import parse_log

        log_file = tmp_path / "test.log"
        log_file.write_text(NO_ARCH_LOG)

        result = parse_log(str(log_file))
        assert result is None


class TestParseMemoryBreakdown:
    def test_parse_breakdown_success(self, tmp_path):
        from services.model_parser import parse_memory_breakdown

        log_content = SAMPLE_LOG.replace(
            "common_memory_breakdown_print: | info | 24124 = 23259 + (20791 = 15345 +    4950 +     495) + remaining",
            "common_memory_breakdown_print: | info | 24124 = 23259 + (20791 = 15345 +    4950 +     495 +     0) + rest"
        )
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_memory_breakdown(str(log_file))

        assert result is not None
        assert result["total_mb"] == 24124
        assert result["free_mb"] == 23259
        assert result["self_mb"] == 20791
        assert result["model_mb"] == 15345
        assert result["context_mb"] == 4950
        assert result["compute_mb"] == 495

    def test_parse_breakdown_no_match(self, tmp_path):
        from services.model_parser import parse_memory_breakdown

        log_file = tmp_path / "test.log"
        log_file.write_text("no breakdown info here\n")

        result = parse_memory_breakdown(str(log_file))
        assert result is None

    def test_parse_breakdown_nonexistent(self):
        from services.model_parser import parse_memory_breakdown

        result = parse_memory_breakdown("/nonexistent/log.log")
        assert result is None


class TestGetOrParseMetadata:
    @patch("services.model_parser.get_conn")
    def test_returns_from_db(self, mock_get_conn):
        from services.model_parser import get_or_parse_metadata

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "model_path": "/path/to/model.gguf",
            "n_layers": 64,
            "n_embd": 5120,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_or_parse_metadata("/path/to/model.gguf")

        assert result is not None
        assert result["n_layers"] == 64

    @patch("services.model_parser.get_conn")
    def test_parses_and_caches_when_db_empty(self, mock_get_conn, tmp_path):
        from services.model_parser import get_or_parse_metadata

        log_file = tmp_path / "test.log"
        log_file.write_text(MINIMAL_LOG)

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        result = get_or_parse_metadata("/path/to/model.gguf", str(log_file))

        assert result is not None
        assert result["n_layers"] == 32
        assert result["model_path"] == "/path/to/model.gguf"
        mock_cursor.execute.assert_called()  # Should have cached to DB

    def test_returns_none_when_no_data(self, tmp_path):
        from services.model_parser import get_or_parse_metadata

        with patch("services.model_parser.get_conn") as mock_get_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_get_conn.return_value.__enter__.return_value = mock_conn

            result = get_or_parse_metadata("/path/to/model.gguf")
            assert result is None


class TestSizeParsing:
    def test_gib_conversion(self, tmp_path):
        from services.model_parser import parse_log

        log_content = "print_info: n_layer = 32\nfile size   = 1.00 GiB\n"
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_log(str(log_file))
        assert result["file_size_bytes"] == 1024 ** 3

    def test_mib_conversion(self, tmp_path):
        from services.model_parser import parse_log

        log_content = "print_info: n_layer = 32\nfile size   = 512.00 MiB\n"
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_log(str(log_file))
        assert result["file_size_bytes"] == int(512 * (1024 ** 2))

    def test_kib_conversion(self, tmp_path):
        from services.model_parser import parse_log

        log_content = "print_info: n_layer = 32\nfile size   = 1024.00 KiB\n"
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_log(str(log_file))
        assert result["file_size_bytes"] == int(1024 * 1024)


class TestParseSizeToBytes:
    def test_gib(self):
        from services.model_parser import _parse_size_to_bytes

        assert _parse_size_to_bytes("1.5", "GiB") == int(1.5 * (1024 ** 3))

    def test_mib(self):
        from services.model_parser import _parse_size_to_bytes

        assert _parse_size_to_bytes("256", "MiB") == 256 * (1024 ** 2)

    def test_kib(self):
        from services.model_parser import _parse_size_to_bytes

        assert _parse_size_to_bytes("1024", "KiB") == 1024 * 1024

    def test_bytes(self):
        from services.model_parser import _parse_size_to_bytes

        assert _parse_size_to_bytes("512", "B") == 512

    def test_unknown_unit_defaults_to_1(self):
        from services.model_parser import _parse_size_to_bytes

        assert _parse_size_to_bytes("100", "XB") == 100


class TestGetCtxFromLog:
    def test_extract_ctx_from_log(self, tmp_path):
        from services.model_parser import _get_ctx_from_log

        log_file = tmp_path / "test.log"
        log_file.write_text(SAMPLE_LOG)

        result = _get_ctx_from_log(str(log_file))
        assert result == 32768

    def test_no_ctx_in_log(self, tmp_path):
        from services.model_parser import _get_ctx_from_log

        log_file = tmp_path / "test.log"
        log_file.write_text("print_info: n_layer = 32\n")

        result = _get_ctx_from_log(str(log_file))
        assert result is None


class TestMemoryBreakdownDerivedFields:
    def test_ctx_per_token_mb_calculated(self, tmp_path):
        from services.model_parser import parse_memory_breakdown

        log_content = (
            "print_info: n_ctx = 4096\n"
            "common_memory_breakdown_print: | info | 24124 = 23259 + "
            "(20791 = 15345 + 4096 + 495 + 0) + rest\n"
        )
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_memory_breakdown(str(log_file))

        assert result is not None
        assert result["ctx_per_token_mb"] is not None
        assert abs(result["ctx_per_token_mb"] - (4096 / 4096)) < 0.01

    def test_est_max_ctx_tokens_calculated(self, tmp_path):
        from services.model_parser import parse_memory_breakdown

        log_content = (
            "print_info: n_ctx = 4096\n"
            "common_memory_breakdown_print: | info | 24124 = 23259 + "
            "(20791 = 15345 + 4096 + 495 + 0) + rest\n"
        )
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_memory_breakdown(str(log_file))

        assert result is not None
        assert result["est_max_ctx_tokens"] is not None
        # free_mb / ctx_per_token_mb = 23259 / 1.0 = 23259
        assert result["est_max_ctx_tokens"] == 23259

    def test_zero_context_gives_none_derived(self, tmp_path):
        from services.model_parser import parse_memory_breakdown

        log_content = (
            "print_info: n_ctx = 4096\n"
            "common_memory_breakdown_print: | info | 24124 = 23259 + "
            "(20791 = 15345 + 0 + 495 + 0) + rest\n"
        )
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_memory_breakdown(str(log_file))

        assert result is not None
        assert result["ctx_per_token_mb"] is None
        assert result["est_max_ctx_tokens"] is None


class TestRegexEdgeCases:
    def test_print_info_extra_whitespace(self, tmp_path):
        from services.model_parser import parse_log

        log_content = "   print_info:  n_layer     =  64\n"
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_log(str(log_file))
        assert result["n_layers"] == 64

    def test_print_info_string_value(self, tmp_path):
        from services.model_parser import parse_log

        log_content = "print_info: architecture = llama\n"
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_log(str(log_file))
        assert result["architecture"] == "llama"

    def test_file_size_with_bpw_parenthesis(self, tmp_path):
        from services.model_parser import parse_log

        log_content = (
            "print_info: n_layer = 32\n"
            "file size   = 15.65 GiB (5.00 BPW)\n"
        )
        log_file = tmp_path / "test.log"
        log_file.write_text(log_content)

        result = parse_log(str(log_file))
        assert result["file_size_bytes"] == int(15.65 * (1024 ** 3))
