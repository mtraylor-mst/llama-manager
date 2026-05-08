from unittest.mock import patch


class TestBuildCommand:
    """Test full command generation with mocked DB data."""

    def _mock_data(self, **overrides):
        """Helper to build mock version data with overrides."""
        data = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "context_batching": {},
            "cpu_threading": {},
            "gpu_device": {},
            "memory": {},
            "sampling": {},
            "server": {},
            "speculative": {},
            "chat_templates": {},
            "checkpoints": {},
            "logging": {},
            "advanced": {},
            "lora_adapters": [],
            "control_vectors": [],
            "logit_biases": [],
            "override_kv": [],
            "override_tensors": [],
            "dry_sequence_breakers": [],
        }
        for key, val in overrides.items():
            if key in data and isinstance(data[key], dict):
                data[key].update(val)
            else:
                data[key] = val
        return data

    @patch("models.configs.get_all_version_data")
    def test_model_path_first(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data()
        cmd = build_command(1)
        assert cmd[0].endswith("llama-server")
        assert "-m" in cmd
        idx = cmd.index("-m")
        assert cmd[idx + 1] == "/models/test.gguf"

    @patch("models.configs.get_all_version_data")
    def test_simple_flags(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            context_batching={"ctx_size": 4096},
            cpu_threading={"threads": 8},
        )
        cmd = build_command(1)
        assert "--ctx-size" in cmd
        assert "--threads" in cmd

    @patch("models.configs.get_all_version_data")
    def test_bool_flag_enabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            memory={"mmap": 1},
        )
        cmd = build_command(1)
        assert "--mmap" in cmd

    @patch("models.configs.get_all_version_data")
    def test_bool_flag_disabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            memory={"mmap": 0},
        )
        cmd = build_command(1)
        assert "--no-mmap" in cmd

    @patch("models.configs.get_all_version_data")
    def test_prefill_assistant_disabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            chat_templates={"prefill_assistant": 0},
        )
        cmd = build_command(1)
        assert "--no-prefill-assistant" in cmd

    @patch("models.configs.get_all_version_data")
    def test_prefill_assistant_enabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            chat_templates={"prefill_assistant": 1},
        )
        cmd = build_command(1)
        assert "--prefill-assistant" in cmd
        assert "--no-prefill-assistant" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_lora_adapters(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            lora_adapters=[{"path": "/lora/adapter.gguf", "scale": 0.8}],
        )
        cmd = build_command(1)
        assert "--lora" in cmd

    @patch("models.configs.get_all_version_data")
    def test_empty_minimal(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(model_loading={})
        cmd = build_command(1)
        assert len(cmd) >= 1

    @patch("models.configs.get_all_version_data")
    def test_sampling_floats(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            sampling={"temperature": 0.8, "top_p": 0.95},
        )
        cmd = build_command(1)
        assert "--temperature" in cmd
        assert "--top-p" in cmd


class TestBuildCommandString:
    """Test command string generation with secret redaction."""

    @patch("models.configs.get_all_version_data")
    def test_basic_string(self, mock_data):
        from services.command_builder import build_command_string

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "context_batching": {},
            "cpu_threading": {},
            "gpu_device": {},
            "memory": {},
            "sampling": {},
            "server": {},
            "speculative": {},
            "chat_templates": {},
            "checkpoints": {},
            "logging": {},
            "advanced": {},
            "lora_adapters": [],
            "control_vectors": [],
            "logit_biases": [],
            "override_kv": [],
            "override_tensors": [],
            "dry_sequence_breakers": [],
        }
        result = build_command_string(1)
        assert "llama-server" in result
        assert "/models/test.gguf" in result

    @patch("models.configs.get_all_version_data")
    def test_redact_hf_token(self, mock_data):
        from services.command_builder import build_command_string

        mock_data.return_value = {
            "model_loading": {"hf_repo": "user/model", "hf_token": "secret123"},
            "context_batching": {},
            "cpu_threading": {},
            "gpu_device": {},
            "memory": {},
            "sampling": {},
            "server": {},
            "speculative": {},
            "chat_templates": {},
            "checkpoints": {},
            "logging": {},
            "advanced": {},
            "lora_adapters": [],
            "control_vectors": [],
            "logit_biases": [],
            "override_kv": [],
            "override_tensors": [],
            "dry_sequence_breakers": [],
        }
        result = build_command_string(1, redact_secrets=True)
        assert "secret123" not in result
        assert "***" in result
