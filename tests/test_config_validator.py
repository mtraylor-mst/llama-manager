"""Tests for services/config_validator.py."""

from unittest.mock import patch


class TestValidateNoModelSource:
    @patch("services.config_validator.get_all_version_data")
    def test_empty_model_loading(self, mock_data):
        from services.config_validator import validate

        mock_data.return_value = {"model_loading": {}}
        errors, warnings = validate(1)

        assert any(e["field"] == "model_source" for e in errors)

    @patch("services.config_validator.get_all_version_data")
    def test_missing_model_loading(self, mock_data):
        from services.config_validator import validate

        mock_data.return_value = {}
        errors, warnings = validate(1)

        assert any(e["field"] == "model_source" for e in errors)

    @patch("services.config_validator.get_all_version_data")
    def test_hf_repo_no_error(self, mock_data):
        """hf_repo is a valid model source — no error."""
        from services.config_validator import validate

        mock_data.return_value = {"model_loading": {"hf_repo": "user/model"}}
        errors, warnings = validate(1)

        assert not any(e["field"] == "model_source" for e in errors)

    @patch("services.config_validator.get_all_version_data")
    def test_model_url_no_error(self, mock_data):
        """model_url is a valid model source — no error."""
        from services.config_validator import validate

        mock_data.return_value = {"model_loading": {"model_url": "https://example.com/model.gguf"}}
        errors, warnings = validate(1)

        assert not any(e["field"] == "model_source" for e in errors)


class TestValidateModelFileExists:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_file_not_found(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_exists.return_value = False
        errors, warnings = validate(1)

        assert any("not found" in e["message"] for e in errors)

    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_file_exists_no_error(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert not any(e["field"] == "model_path" for e in errors)


class TestValidateDraftModel:
    @patch("services.config_validator.get_or_parse_metadata")
    @patch("services.config_validator.theoretical_estimate")
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_draft_not_found(self, mock_data, mock_exists, mock_vram, mock_meta):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {
                "model_path": "/models/main.gguf",
                "model_draft": "/models/draft.gguf",
            },
        }
        mock_exists.side_effect = lambda p: "draft" not in p  # main exists, draft doesn't
        mock_vram.return_value = None
        mock_meta.return_value = {"n_layers": 32}
        errors, warnings = validate(1)

        assert any(e["field"] == "model_draft" for e in errors)

    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_draft_exists_ok(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {
                "model_path": "/models/main.gguf",
                "model_draft": "/models/draft.gguf",
            },
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert not any(e["field"] == "model_draft" for e in errors)


class TestValidateMmproj:
    @patch("services.config_validator.get_or_parse_metadata")
    @patch("services.config_validator.theoretical_estimate")
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_mmproj_not_found(self, mock_data, mock_exists, mock_vram, mock_meta):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {
                "model_path": "/models/test.gguf",
                "mmproj_path": "/models/mmproj.gguf",
            },
        }
        mock_exists.side_effect = lambda p: "mmproj" not in p  # model ok, mmproj missing
        mock_vram.return_value = None
        mock_meta.return_value = {"n_layers": 32}
        errors, warnings = validate(1)

        assert any(e["field"] == "mmproj_path" for e in errors)


class TestValidatePositiveInts:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_zero_ctx_size(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "context_batching": {"ctx_size": 0},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert any("ctx_size" in w["field"] for w in warnings)

    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_negative_threads(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "cpu_threading": {"threads": -1},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert any("threads" in w["field"] for w in warnings)

    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_valid_positive_values(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "context_batching": {"ctx_size": 8192},
            "cpu_threading": {"threads": 8},
            "gpu_device": {"gpu_layers": 33},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert not any("ctx_size" in w["field"] or "threads" in w["field"] for w in warnings)


class TestValidateNonNegative:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_negative_port(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "server": {"port": -1},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert any("port" in w["field"] for w in warnings)

    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_zero_port_ok(self, mock_data, mock_exists):
        """Port 0 is valid (OS assigns ephemeral port)."""
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "server": {"port": 0},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert not any("port" in w["field"] for w in warnings)


class TestValidateVramGreen:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_green_vram_no_warning(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = {
                "status": "green",
                "margin_pct": 40,
                "predicted_peak_mb": 12000,
                "total_vram_mb": 24576,
            }
            errors, warnings = validate(1)

        assert not any(w["field"] == "vram" for w in warnings)


class TestValidateVramYellow:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_yellow_vram_warning(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = {
                "status": "yellow",
                "margin_pct": 8,
                "predicted_peak_mb": 22600,
                "total_vram_mb": 24576,
            }
            errors, warnings = validate(1)

        assert any(w["field"] == "vram" and "Low VRAM margin" in w["message"] for w in warnings)


class TestValidateVramRed:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_red_vram_warning(self, mock_data, mock_exists):
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = {
                "status": "red",
                "margin_pct": -5,
                "predicted_peak_mb": 26000,
                "total_vram_mb": 24576,
            }
            errors, warnings = validate(1)

        assert any(w["field"] == "vram" and "insufficient" in w["message"] for w in warnings)


class TestValidateNoMetadata:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_no_metadata_warning(self, mock_data, mock_exists):
        """When model exists but no cached metadata, warn about VRAM estimation."""
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = None
                errors, warnings = validate(1)

        assert any(w["field"] == "vram" and "Cannot estimate" in w["message"] for w in warnings)


class TestValidateNoMetadataSkipped:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_no_metadata_skipped_when_no_model(self, mock_data, mock_exists):
        """Don't warn about missing metadata when model_path is empty."""
        from services.config_validator import validate

        mock_data.return_value = {"model_loading": {}}
        errors, warnings = validate(1)

        # Should have model_path error but no vram warning
        assert not any(w["field"] == "vram" for w in warnings)


class TestValidateLoadError:
    @patch("services.config_validator.get_all_version_data")
    def test_db_error(self, mock_data):
        from services.config_validator import validate

        mock_data.side_effect = Exception("Connection refused")
        errors, warnings = validate(1)

        assert len(errors) == 1
        assert "Could not load" in errors[0]["message"]


class TestValidateMultipleIssues:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_multiple_warnings_accumulate(self, mock_data, mock_exists):
        """Multiple validation issues should all be reported."""
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "context_batching": {"ctx_size": 0},
            "cpu_threading": {"threads": -1},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = {
                "status": "red",
                "margin_pct": -10,
                "predicted_peak_mb": 30000,
                "total_vram_mb": 24576,
            }
            errors, warnings = validate(1)

        # Should have both int warnings and VRAM warning
        assert any("ctx_size" in w["field"] for w in warnings)
        assert any("threads" in w["field"] for w in warnings)
        assert any(w["field"] == "vram" for w in warnings)

    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_errors_and_warnings_both_returned(self, mock_data, mock_exists):
        """Errors and warnings can coexist."""
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {
                "model_path": "/models/test.gguf",
                "mmproj_path": "/models/missing.gguf",
            },
        }
        mock_exists.side_effect = [True, False]  # model ok, mmproj missing

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = {
                "status": "yellow",
                "margin_pct": 3,
                "predicted_peak_mb": 24000,
                "total_vram_mb": 24576,
            }
            errors, warnings = validate(1)

        assert any(e["field"] == "mmproj_path" for e in errors)
        assert any(w["field"] == "vram" for w in warnings)


class TestValidateNoneValues:
    @patch("services.config_validator.os.path.exists")
    @patch("services.config_validator.get_all_version_data")
    def test_none_values_skipped(self, mock_data, mock_exists):
        """None values should not trigger validation (they mean 'use default')."""
        from services.config_validator import validate

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "context_batching": {"ctx_size": None},
            "cpu_threading": {"threads": None},
            "gpu_device": {"gpu_layers": None},
        }
        mock_exists.return_value = True

        with patch("services.config_validator.theoretical_estimate") as mock_vram:
            mock_vram.return_value = None
            with patch("services.config_validator.get_or_parse_metadata") as mock_meta:
                mock_meta.return_value = {"n_layers": 32}
                errors, warnings = validate(1)

        assert not any("ctx_size" in w["field"] for w in warnings)
        assert not any("threads" in w["field"] for w in warnings)
