"""Tests for services/vram_safety.py."""

from unittest.mock import patch


class TestKvQuantBytes:
    def test_f16(self):
        from services.vram_safety import _kv_quant_bytes
        assert _kv_quant_bytes("f16") == 2

    def test_q8_0(self):
        from services.vram_safety import _kv_quant_bytes
        assert _kv_quant_bytes("q8_0") == 1

    def test_q4_0(self):
        from services.vram_safety import _kv_quant_bytes
        assert _kv_quant_bytes("q4_0") == 0.5

    def test_q5_0(self):
        from services.vram_safety import _kv_quant_bytes
        assert _kv_quant_bytes("q5_0") == 0.625

    def test_unknown_defaults_to_f16(self):
        from services.vram_safety import _kv_quant_bytes
        assert _kv_quant_bytes("unknown_type") == 2

    def test_none_defaults_to_f16(self):
        from services.vram_safety import _kv_quant_bytes
        assert _kv_quant_bytes(None) == 2


class TestColorFromMargin:
    def test_green(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(25) == "green"

    def test_green_at_threshold(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(20) == "green"

    def test_yellow_high(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(19.9) == "yellow"

    def test_yellow_at_threshold(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(5) == "yellow"

    def test_red_low(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(4.9) == "red"

    def test_red_negative(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(-10) == "red"


class TestTheoreticalEstimate:
    @patch("services.vram_safety.VramMonitor.get_total_vram")
    @patch("services.vram_safety.get_or_parse_metadata")
    @patch("services.vram_safety.get_category")
    @patch("services.vram_safety.get_all_version_data")
    def test_basic_calculation(
        self, mock_all_data, mock_category, mock_meta, mock_total_vram
    ):
        from services.vram_safety import theoretical_estimate

        mock_all_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_category.side_effect = [
            {"ctx_size": 8192},  # context_batching
            {"cache_type_k": "f16"},  # memory
        ]
        mock_meta.return_value = {
            "file_size_bytes": 16 * 1024 * 1024 * 1024,  # 16 GiB
            "n_layers": 64,
            "n_embd": 5120,
            "n_head": 40,
            "n_head_kv": 8,
        }
        mock_total_vram.return_value = 24576  # 24 GB

        result = theoretical_estimate(1)

        assert result is not None
        assert result["source"] == "theoretical"
        assert result["confidence"] == "low"
        assert result["total_vram_mb"] == 24576
        assert result["weight_size_mb"] == 16384
        # KV cache: 2 * 64 * 8 * (5120/40) * 2 bytes per token
        # = 2 * 64 * 8 * 128 * 2 = 262144 bytes per token
        assert result["kv_per_token_bytes"] == 262144.0

    @patch("services.vram_safety.VramMonitor.get_total_vram")
    @patch("services.vram_safety.get_or_parse_metadata")
    @patch("services.vram_safety.get_all_version_data")
    def test_no_model_path(self, mock_all_data, mock_meta, mock_total_vram):
        from services.vram_safety import theoretical_estimate

        mock_all_data.return_value = {"model_loading": {}}
        result = theoretical_estimate(1)
        assert result is None

    @patch("services.vram_safety.VramMonitor.get_total_vram")
    @patch("services.vram_safety.get_all_version_data")
    def test_no_metadata(self, mock_all_data, mock_total_vram):
        from services.vram_safety import theoretical_estimate

        mock_all_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        with patch("services.vram_safety.get_or_parse_metadata") as mock_meta:
            mock_meta.return_value = None
            result = theoretical_estimate(1)
            assert result is None

    @patch("services.vram_safety.VramMonitor.get_total_vram")
    @patch("services.vram_safety.get_or_parse_metadata")
    @patch("services.vram_safety.get_category")
    @patch("services.vram_safety.get_all_version_data")
    def test_status_colors(
        self, mock_all_data, mock_category, mock_meta, mock_total_vram
    ):
        """Test that different VRAM configurations produce correct color statuses."""
        from services.vram_safety import theoretical_estimate

        mock_all_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_category.return_value = {
            "ctx_size": 2048,
            "cache_type_k": "f16",
        }
        mock_meta.return_value = {
            "file_size_bytes": 4 * 1024 * 1024 * 1024,  # 4 GiB
            "n_layers": 32,
            "n_embd": 4096,
            "n_head": 32,
            "n_head_kv": 4,
        }

        # Green: plenty of VRAM
        mock_total_vram.return_value = 24576
        result = theoretical_estimate(1)
        assert result["status"] == "green"

        # Red: very tight VRAM
        mock_total_vram.return_value = 5000
        result = theoretical_estimate(1)
        assert result["status"] in ("red", "yellow")


class TestEmpiricalEstimate:
    @patch("services.vram_safety.get_latest_stress_test")
    @patch("services.vram_safety.get_category")
    def test_empirical_with_data(self, mock_category, mock_test):
        from services.vram_safety import empirical_estimate

        mock_test.return_value = {
            "status": "completed",
            "kv_per_token_bytes": 131072,
            "compaction_coefficient": 0.05,
            "model_weight_size_mb": 8192,
            "total_vram_mb": 24576,
            "failure_ctx_tokens": 32000,
            "id": 1,
        }
        mock_category.return_value = {"ctx_size": 8192}

        result = empirical_estimate(1)

        assert result is not None
        assert result["source"] == "empirical"
        assert result["confidence"] == "high"
        assert result["compaction_coefficient"] == 0.05

    @patch("services.vram_safety.get_latest_stress_test")
    def test_no_test_data(self, mock_test):
        from services.vram_safety import empirical_estimate

        mock_test.return_value = None
        result = empirical_estimate(1)
        assert result is None

    @patch("services.vram_safety.get_latest_stress_test")
    def test_incomplete_test(self, mock_test):
        from services.vram_safety import empirical_estimate

        mock_test.return_value = {"status": "running"}
        result = empirical_estimate(1)
        assert result is None


class TestGetSafety:
    @patch("services.vram_safety.empirical_estimate")
    @patch("services.vram_safety.theoretical_estimate")
    def test_prefers_empirical(self, mock_theoretical, mock_empirical):
        from services.vram_safety import get_safety

        mock_empirical.return_value = {"source": "empirical", "margin_pct": 15}
        mock_theoretical.return_value = {"source": "theoretical", "margin_pct": 25}

        result = get_safety(1)

        assert result["source"] == "empirical"
        mock_theoretical.assert_not_called()

    @patch("services.vram_safety.empirical_estimate")
    @patch("services.vram_safety.theoretical_estimate")
    def test_falls_back_to_theoretical(self, mock_theoretical, mock_empirical):
        from services.vram_safety import get_safety

        mock_empirical.return_value = None
        mock_theoretical.return_value = {"source": "theoretical", "margin_pct": 25}

        result = get_safety(1)

        assert result["source"] == "theoretical"

    @patch("services.vram_safety.empirical_estimate")
    @patch("services.vram_safety.theoretical_estimate")
    def test_returns_none_when_both_fail(self, mock_theoretical, mock_empirical):
        from services.vram_safety import get_safety

        mock_empirical.return_value = None
        mock_theoretical.return_value = None

        result = get_safety(1)
        assert result is None


class TestTheoreticalQuantization:
    @patch("services.vram_safety.VramMonitor.get_total_vram")
    @patch("services.vram_safety.get_or_parse_metadata")
    @patch("services.vram_safety.get_category")
    @patch("services.vram_safety.get_all_version_data")
    def test_q4_0_quantization(
        self, mock_all_data, mock_category, mock_meta, mock_total_vram
    ):
        """q4_0 uses 0.5 bytes per element, reducing KV cache by half vs f16."""
        from services.vram_safety import theoretical_estimate

        mock_all_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_category.side_effect = [
            {"ctx_size": 8192},
            {"cache_type_k": "q4_0"},
        ]
        mock_meta.return_value = {
            "file_size_bytes": 4 * 1024 * 1024 * 1024,
            "n_layers": 32,
            "n_embd": 4096,
            "n_head": 32,
            "n_head_kv": 4,
        }
        mock_total_vram.return_value = 24576

        result = theoretical_estimate(1)

        assert result is not None
        # head_dim = 4096/32 = 128, kv_bytes = 0.5 (q4_0)
        # kv_per_token = 2 * 32 * 4 * 128 * 0.5 = 16384
        assert result["kv_per_token_bytes"] == 16384.0


class TestTheoreticalNHeadKvFallback:
    @patch("services.vram_safety.VramMonitor.get_total_vram")
    @patch("services.vram_safety.get_or_parse_metadata")
    @patch("services.vram_safety.get_category")
    @patch("services.vram_safety.get_all_version_data")
    def test_n_head_kv_falls_back_to_n_head(
        self, mock_all_data, mock_category, mock_meta, mock_total_vram
    ):
        """When n_head_kv is None, it should fall back to n_head."""
        from services.vram_safety import theoretical_estimate

        mock_all_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_category.side_effect = [
            {"ctx_size": 8192},
            {"cache_type_k": "f16"},
        ]
        mock_meta.return_value = {
            "file_size_bytes": 4 * 1024 * 1024 * 1024,
            "n_layers": 32,
            "n_embd": 4096,
            "n_head": 32,
            "n_head_kv": None,  # Should fall back to n_head=32
        }
        mock_total_vram.return_value = 24576

        result = theoretical_estimate(1)

        assert result is not None
        # head_dim = 4096/32 = 128, kv_bytes = 2 (f16), n_head_kv = 32
        # kv_per_token = 2 * 32 * 32 * 128 * 2 = 524288
        assert result["kv_per_token_bytes"] == 524288.0


class TestEmpiricalEdgeCases:
    @patch("services.vram_safety.get_latest_stress_test")
    @patch("services.vram_safety.get_category")
    def test_negative_compaction_falls_back(self, mock_category, mock_test):
        """Negative compaction coefficient should use theoretical buffer."""
        from services.vram_safety import empirical_estimate

        mock_test.return_value = {
            "status": "completed",
            "kv_per_token_bytes": 131072,
            "compaction_coefficient": -1,  # Invalid, should fall back
            "model_weight_size_mb": 8192,
            "total_vram_mb": 24576,
            "id": 1,
        }
        mock_category.return_value = {"ctx_size": 8192}

        result = empirical_estimate(1)

        assert result is not None
        assert result["compaction_coefficient"] == -1

    @patch("services.vram_safety.get_latest_stress_test")
    def test_missing_required_fields(self, mock_test):
        """Missing kv_per_token_bytes should return None."""
        from services.vram_safety import empirical_estimate

        mock_test.return_value = {
            "status": "completed",
            "model_weight_size_mb": 8192,
            "total_vram_mb": 24576,
            "id": 1,
        }
        result = empirical_estimate(1)
        assert result is None

    @patch("services.vram_safety.get_latest_stress_test")
    def test_zero_kv_per_token_bytes(self, mock_test):
        """Zero kv_per_token_bytes should return None."""
        from services.vram_safety import empirical_estimate

        mock_test.return_value = {
            "status": "completed",
            "kv_per_token_bytes": 0,
            "model_weight_size_mb": 8192,
            "total_vram_mb": 24576,
            "id": 1,
        }
        result = empirical_estimate(1)
        assert result is None


class TestColorThresholdsExact:
    def test_green_just_above(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(20.1) == "green"

    def test_yellow_at_red_boundary(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(5.0) == "yellow"

    def test_red_just_below(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(4.99) == "red"

    def test_zero_margin_is_red(self):
        from services.vram_safety import _color_from_margin
        assert _color_from_margin(0) == "red"
