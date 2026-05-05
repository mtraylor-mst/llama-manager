from services.config_importer import (
    parse_args,
    coerce_value,
    _normalize_flag,
    _extract_model_name,
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
