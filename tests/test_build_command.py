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
    def test_mmproj_auto_disabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            model_loading={"mmproj_auto": 0},
        )
        cmd = build_command(1)
        assert "--no-mmproj" in cmd
        assert "--mmproj-auto" not in cmd
        assert "--mmproj-auto/--no-mmproj" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_mmproj_auto_enabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            model_loading={"mmproj_auto": 1},
        )
        cmd = build_command(1)
        assert "--mmproj-auto" in cmd
        assert "--no-mmproj" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_mmproj_offload_disabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            model_loading={"mmproj_offload": 0},
        )
        cmd = build_command(1)
        assert "--no-mmproj-offload" in cmd
        assert "--mmproj-offload" not in cmd

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
            lora_adapters=[{"path": "/lora/adapter.gguf", "scale": 0.8}]
        )
        cmd = build_command(1)
        # scaled adapters are emitted via --lora-scaled since b10355
        assert "--lora-scaled" in cmd
        assert "/lora/adapter.gguf:0.8" in cmd

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

    @patch("models.configs.get_all_version_data")
    def test_no_redaction(self, mock_data):
        from services.command_builder import build_command_string

        mock_data.return_value = {
            "model_loading": {"model_path": "/models/test.gguf"},
            "context_batching": {},
            "cpu_threading": {},
            "gpu_device": {},
            "memory": {},
            "sampling": {},
            "server": {"api_key": "mysecret"},
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
        result = build_command_string(1, redact_secrets=False)
        assert "mysecret" in result


class TestBuildCommandComplexTables:
    """Test complex table features: control vectors, logit biases, override_kv, etc."""

    def _mock_data(self, **overrides):
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
    def test_control_vector_scaled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            control_vectors=[{"path": "/cv/emotion.bin", "scale": 0.5}]
        )
        cmd = build_command(1)
        assert "--control-vector-scaled" in cmd
        assert "/cv/emotion.bin:0.5" in cmd

    @patch("models.configs.get_all_version_data")
    def test_control_vector_unscaled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            control_vectors=[{"path": "/cv/emotion.bin"}]
        )
        cmd = build_command(1)
        assert "--control-vector" in cmd
        assert "/cv/emotion.bin" in cmd

    @patch("models.configs.get_all_version_data")
    def test_control_vector_with_layer_range(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            control_vectors=[
                {
                    "path": "/cv/emotion.bin",
                    "scale": 0.5,
                    "layer_range_start": 10,
                    "layer_range_end": 20,
                }
            ]
        )
        cmd = build_command(1)
        assert "--control-vector-layer-range" in cmd
        assert "10" in cmd
        assert "20" in cmd

    @patch("models.configs.get_all_version_data")
    def test_logit_biases_positive(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            logit_biases=[{"token_id": 15043, "bias_value": 1.0}]
        )
        cmd = build_command(1)
        assert "--logit-bias" in cmd
        idx = cmd.index("--logit-bias")
        assert "+" in cmd[idx + 1]
        assert "15043" in cmd[idx + 1]

    @patch("models.configs.get_all_version_data")
    def test_logit_biases_negative(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            logit_biases=[{"token_id": 220, "bias_value": -1.0}]
        )
        cmd = build_command(1)
        assert "--logit-bias" in cmd
        idx = cmd.index("--logit-bias")
        assert "-" in cmd[idx + 1]
        assert "220" in cmd[idx + 1]

    @patch("models.configs.get_all_version_data")
    def test_logit_biases_zero(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            logit_biases=[{"token_id": 1, "bias_value": 0}]
        )
        cmd = build_command(1)
        assert "--logit-bias" in cmd
        assert "1+0" in cmd

    @patch("models.configs.get_all_version_data")
    def test_override_kv(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            override_kv=[
                {
                    "key_name": "tokenizer.ggml.tokens",
                    "key_type": "int",
                    "key_value": "4096",
                }
            ]
        )
        cmd = build_command(1)
        assert "--override-kv" in cmd
        assert "tokenizer.ggml.tokens=int:4096" in cmd

    @patch("models.configs.get_all_version_data")
    def test_override_tensors(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            override_tensors=[{"tensor_pattern": "token_embd", "buffer_type": "cpu"}]
        )
        cmd = build_command(1)
        assert "--override-tensor" in cmd
        assert "token_embd=cpu" in cmd

    @patch("models.configs.get_all_version_data")
    def test_dry_sequence_breakers(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            dry_sequence_breakers=[
                {"breaker_char": "."},
                {"breaker_char": "\n"},
            ]
        )
        cmd = build_command(1)
        assert cmd.count("--dry-sequence-breaker") == 2

    @patch("models.configs.get_all_version_data")
    def test_grammar_file_takes_precedence(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            advanced={
                "grammar": 'root ::= "hello"',
                "grammar_file": "/path/to/grammar.gbnf",
            }
        )
        cmd = build_command(1)
        assert "--grammar-file" in cmd
        assert "--grammar" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_json_schema_file(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            advanced={"json_schema_file": "/path/to/schema.json"}
        )
        cmd = build_command(1)
        assert "--json-schema-file" in cmd
        assert "/path/to/schema.json" in cmd

    @patch("models.configs.get_all_version_data")
    def test_model_draft(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            model_loading={
                "model_path": "/models/main.gguf",
                "model_draft": "/models/draft.gguf",
            }
        )
        cmd = build_command(1)
        assert "--model-draft" in cmd
        assert "/models/draft.gguf" in cmd

    @patch("models.configs.get_all_version_data")
    def test_model_vocoder_not_emitted(self, mock_data):
        # --model-vocoder was removed in llama.cpp b10355
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            model_loading={
                "model_path": "/models/main.gguf",
                "model_vocoder": "/models/vocoder.gguf",
            }
        )
        cmd = build_command(1)
        assert "--model-vocoder" not in cmd
        assert "/models/vocoder.gguf" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_lora_paths_fallback(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            model_loading={
                "model_path": "/models/test.gguf",
                "lora_paths": "/lora/adapter.gguf",
            },
            lora_adapters=[],
        )
        cmd = build_command(1)
        assert "--lora" in cmd
        assert "/lora/adapter.gguf" in cmd

    @patch("models.configs.get_all_version_data")
    def test_lora_paths_not_used_when_structured_lora_exists(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            model_loading={
                "model_path": "/models/test.gguf",
                "lora_paths": "/lora/fallback.gguf",
            },
            lora_adapters=[{"path": "/lora/structured.gguf", "scale": 1.0}],
        )
        cmd = build_command(1)
        assert "--lora-scaled" in cmd
        lora_idx = cmd.index("--lora-scaled")
        assert "structured" in cmd[lora_idx + 1]
        assert "/lora/fallback.gguf" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_api_key(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(server={"api_key": "sk-abc123"})
        cmd = build_command(1)
        assert "--api-key" in cmd
        assert "sk-abc123" in cmd

    @patch("models.configs.get_all_version_data")
    def test_chat_template_kwargs(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            chat_templates={
                "chat_template_kwargs": '{"bos_token": "<|BEGIN|>", "eos_token": "<|END|>"}'
            }
        )
        cmd = build_command(1)
        assert "--chat-template-kwargs" in cmd

    @patch("models.configs.get_all_version_data")
    def test_spec_replace(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"spec_replace_target": "target", "spec_replace_draft": "draft"}
        )
        cmd = build_command(1)
        assert "--spec-replace" in cmd
        assert "target" in cmd
        assert "draft" in cmd

    @patch("models.configs.get_all_version_data")
    def test_spec_replace_not_emitted_without_both(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"spec_replace_target": "target"}
        )
        cmd = build_command(1)
        assert "--spec-replace" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_override_tensor_draft(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"override_tensor_draft": "attn_q=cpu"}
        )
        cmd = build_command(1)
        assert "--override-tensor-draft" in cmd
        assert "attn_q=cpu" in cmd

    @patch("models.configs.get_all_version_data")
    def test_spec_draft_n_max(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"spec_draft_n_max": 16}
        )
        cmd = build_command(1)
        assert "--spec-draft-n-max" in cmd
        assert "16" in cmd

    @patch("models.configs.get_all_version_data")
    def test_spec_type(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"spec_type": "draft-mtp"}
        )
        cmd = build_command(1)
        assert "--spec-type" in cmd
        assert "draft-mtp" in cmd


class TestBuildCommandB10355:
    """Flags removed/changed/deprecated in llama.cpp build 10355."""

    def _mock_data(self, **overrides):
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
    def test_load_mode_emitted(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            memory={"load_mode": "mmap+mlock"}
        )
        cmd = build_command(1)
        idx = cmd.index("--load-mode")
        assert cmd[idx + 1] == "mmap+mlock"

    @patch("models.configs.get_all_version_data")
    def test_load_mode_suppresses_deprecated_flags(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            memory={"load_mode": "mlock", "mmap": 1, "mlock": 1, "direct_io": 1}
        )
        cmd = build_command(1)
        assert "--load-mode" in cmd
        assert "--mmap" not in cmd
        assert "--no-mmap" not in cmd
        assert "--mlock" not in cmd
        assert "--direct-io" not in cmd
        assert "--no-direct-io" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_deprecated_flags_emitted_without_load_mode(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(memory={"mmap": 1, "mlock": 1})
        cmd = build_command(1)
        assert "--mmap" in cmd
        assert "--mlock" in cmd
        assert "--load-mode" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_removed_draft_flags_not_emitted(self, mock_data):
        # --draft-max and --draft-min were removed in b10355
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"draft_max": 16, "draft_min": 2, "ctx_size_draft": 4096}
        )
        cmd = build_command(1)
        assert "--draft-max" not in cmd
        assert "--draft" not in cmd
        assert "--draft-min" not in cmd
        assert "--ctx-size-draft" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_spec_draft_n_min(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"spec_draft_n_min": 2}
        )
        cmd = build_command(1)
        assert "--spec-draft-n-min" in cmd
        assert "2" in cmd

    @patch("models.configs.get_all_version_data")
    def test_draft_p_min_uses_spec_flag(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"draft_p_min": 0.75}
        )
        cmd = build_command(1)
        assert "--spec-draft-p-min" in cmd

    @patch("models.configs.get_all_version_data")
    def test_spec_draft_p_split(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={"spec_draft_p_split": 0.2}
        )
        cmd = build_command(1)
        idx = cmd.index("--spec-draft-p-split")
        assert cmd[idx + 1] == "0.2"

    @patch("models.configs.get_all_version_data")
    def test_removed_ngram_flags_not_emitted(self, mock_data):
        # generic --spec-ngram-* flags were removed in b10355
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={
                "spec_ngram_size_n": 12,
                "spec_ngram_size_m": 48,
                "spec_ngram_min_hits": 3,
            }
        )
        cmd = build_command(1)
        assert "--spec-ngram-size-n" not in cmd
        assert "--spec-ngram-size-m" not in cmd
        assert "--spec-ngram-min-hits" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_per_type_ngram_flags(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            speculative={
                "spec_ngram_simple_size_n": 12,
                "spec_ngram_simple_size_m": 48,
                "spec_ngram_simple_min_hits": 2,
                "spec_ngram_map_k_size_n": 10,
                "spec_ngram_map_k_size_m": 40,
                "spec_ngram_map_k_min_hits": 1,
                "spec_ngram_map_k4v_size_n": 11,
                "spec_ngram_map_k4v_size_m": 41,
                "spec_ngram_map_k4v_min_hits": 3,
                "spec_ngram_mod_n_min": 48,
                "spec_ngram_mod_n_max": 64,
                "spec_ngram_mod_n_match": 24,
            }
        )
        cmd = build_command(1)
        for flag in (
            "--spec-ngram-simple-size-n",
            "--spec-ngram-simple-size-m",
            "--spec-ngram-simple-min-hits",
            "--spec-ngram-map-k-size-n",
            "--spec-ngram-map-k-size-m",
            "--spec-ngram-map-k-min-hits",
            "--spec-ngram-map-k4v-size-n",
            "--spec-ngram-map-k4v-size-m",
            "--spec-ngram-map-k4v-min-hits",
            "--spec-ngram-mod-n-min",
            "--spec-ngram-mod-n-max",
            "--spec-ngram-mod-n-match",
        ):
            assert flag in cmd

    @patch("models.configs.get_all_version_data")
    def test_checkpoint_min_step(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            checkpoints={"checkpoint_min_step": 4096}
        )
        cmd = build_command(1)
        assert "--checkpoint-min-step" in cmd
        assert "4096" in cmd

    @patch("models.configs.get_all_version_data")
    def test_checkpoint_every_nt_not_emitted(self, mock_data):
        # --checkpoint-every-n-tokens was removed in b10355
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            checkpoints={"checkpoint_every_nt": 1000}
        )
        cmd = build_command(1)
        assert "--checkpoint-every-n-tokens" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_lora_split_into_scaled(self, mock_data):
        # scaled adapters must use --lora-scaled since b10355
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            lora_adapters=[
                {"path": "/lora/plain.gguf"},
                {"path": "/lora/scaled.gguf", "scale": 0.5},
            ]
        )
        cmd = build_command(1)
        lora_idx = cmd.index("--lora")
        assert cmd[lora_idx + 1] == "/lora/plain.gguf"
        scaled_idx = cmd.index("--lora-scaled")
        assert cmd[scaled_idx + 1] == "/lora/scaled.gguf:0.5"

    @patch("models.configs.get_all_version_data")
    def test_lora_all_scaled_uses_lora_scaled_only(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            lora_adapters=[
                {"path": "/lora/a.gguf", "scale": 0.8},
                {"path": "/lora/b.gguf", "scale": 1.0},
            ]
        )
        cmd = build_command(1)
        assert "--lora-scaled" in cmd
        assert "--lora" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_webui_mcp_proxy_enabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            server={"webui_mcp_proxy": 1}
        )
        cmd = build_command(1)
        assert "--ui-mcp-proxy" in cmd
        assert "--no-ui-mcp-proxy" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_webui_mcp_proxy_disabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            server={"webui_mcp_proxy": 0}
        )
        cmd = build_command(1)
        assert "--no-ui-mcp-proxy" in cmd
        assert "--ui-mcp-proxy" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_ui_config_flags(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            server={
                "webui_config": '{"theme":"dark"}',
                "webui_config_file": "/etc/ui.json",
                "tools": "all",
            }
        )
        cmd = build_command(1)
        idx = cmd.index("--ui-config")
        assert cmd[idx + 1] == '{"theme":"dark"}'
        assert "--ui-config-file" in cmd
        assert cmd[cmd.index("--ui-config-file") + 1] == "/etc/ui.json"
        assert "--tools" in cmd
        idx = cmd.index("--tools")
        assert cmd[idx + 1] == "all"


    @patch("models.configs.get_all_version_data")
    def test_reasoning_preserve_enabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            chat_templates={"reasoning_preserve": 1}
        )
        cmd = build_command(1)
        assert "--reasoning-preserve" in cmd
        assert "--no-reasoning-preserve" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_reasoning_preserve_disabled(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            chat_templates={"reasoning_preserve": 0}
        )
        cmd = build_command(1)
        assert "--no-reasoning-preserve" in cmd
        assert "--reasoning-preserve" not in cmd

    @patch("models.configs.get_all_version_data")
    def test_reasoning_preserve_default_omitted(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(chat_templates={})
        cmd = build_command(1)
        assert "--reasoning-preserve" not in cmd
        assert "--no-reasoning-preserve" not in cmd


class TestGetModelsInDir:
    def test_returns_gguf_files(self, tmp_path):
        from services.command_builder import get_models_in_dir

        subdir = tmp_path / "sub"
        subdir.mkdir()
        (tmp_path / "model1.gguf").touch()
        (subdir / "model2.gguf").touch()
        (tmp_path / "readme.txt").touch()

        with patch("config.MODEL_DIR", str(tmp_path)):
            models = get_models_in_dir(str(tmp_path))
            assert len(models) == 2
            names = [m["name"] for m in models]
            assert "model1.gguf" in names
            assert "model2.gguf" in names

    def test_returns_empty_for_nonexistent_dir(self, tmp_path):
        from services.command_builder import get_models_in_dir

        models = get_models_in_dir(str(tmp_path / "does_not_exist"))
        assert models == []

    def test_returns_empty_for_empty_dir(self, tmp_path):
        from services.command_builder import get_models_in_dir

        models = get_models_in_dir(str(tmp_path))
        assert models == []

    def test_includes_path_and_rel(self, tmp_path):
        from services.command_builder import get_models_in_dir

        (tmp_path / "model.gguf").touch()

        with patch("config.MODEL_DIR", str(tmp_path)):
            models = get_models_in_dir(str(tmp_path))
            assert len(models) == 1
            m = models[0]
            assert m["path"].endswith("model.gguf")
            assert m["name"] == "model.gguf"
            assert m["rel"] == "model.gguf"

    def test_case_insensitive_gguf(self, tmp_path):
        from services.command_builder import get_models_in_dir

        (tmp_path / "model.GGUF").touch()

        with patch("config.MODEL_DIR", str(tmp_path)):
            models = get_models_in_dir(str(tmp_path))
            assert len(models) == 1


class TestBuildCommandMultipleComplexTables:
    """Test build_command with multiple complex tables populated simultaneously."""

    def _mock_data(self, **overrides):
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
    def test_all_complex_tables(self, mock_data):
        from services.command_builder import build_command

        mock_data.return_value = self._mock_data(
            lora_adapters=[{"path": "/lora/a.gguf", "scale": 1.0}],
            control_vectors=[{"path": "/cv/emotion.bin", "scale": 0.5}],
            logit_biases=[{"token_id": 15043, "bias_value": 1.0}],
            override_kv=[{"key_name": "key1", "key_type": "int", "key_value": "100"}],
            override_tensors=[{"tensor_pattern": "embd", "buffer_type": "cpu"}],
            dry_sequence_breakers=[{"breaker_char": "."}],
        )
        cmd = build_command(1)
        # scaled lora emitted via --lora-scaled since b10355
        assert "--lora-scaled" in cmd
        assert "--control-vector-scaled" in cmd
        assert "--logit-bias" in cmd
        assert "--override-kv" in cmd
        assert "--override-tensor" in cmd
        assert "--dry-sequence-breaker" in cmd
