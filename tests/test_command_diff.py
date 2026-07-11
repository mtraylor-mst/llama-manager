from unittest.mock import patch


class TestParseCommandToDict:
    def test_simple_flag_with_value(self):
        from services.command_diff import _parse_command_to_dict

        args = ["llama-server", "-m", "model.gguf", "-c", "4096"]
        result = _parse_command_to_dict(args)
        assert result["-m"] == "model.gguf"
        assert result["-c"] == "4096"

    def test_boolean_flag(self):
        from services.command_diff import _parse_command_to_dict

        args = ["llama-server", "--mmap", "-c", "4096"]
        result = _parse_command_to_dict(args)
        assert result["--mmap"] is True
        assert result["-c"] == "4096"

    def test_empty_args(self):
        from services.command_diff import _parse_command_to_dict

        result = _parse_command_to_dict([])
        assert result == {}

    def test_non_flag_arg_ignored(self):
        from services.command_diff import _parse_command_to_dict

        args = ["llama-server", "-m", "model.gguf"]
        result = _parse_command_to_dict(args)
        assert "llama-server" not in result
        assert result["-m"] == "model.gguf"

    def test_consecutive_boolean_flags(self):
        from services.command_diff import _parse_command_to_dict

        args = ["llama-server", "--mmap", "--mlock", "--verbose"]
        result = _parse_command_to_dict(args)
        assert result["--mmap"] is True
        assert result["--mlock"] is True
        assert result["--verbose"] is True

    def test_flag_at_end_without_value(self):
        from services.command_diff import _parse_command_to_dict

        args = ["llama-server", "-c", "4096", "--mmap"]
        result = _parse_command_to_dict(args)
        assert result["-c"] == "4096"
        assert result["--mmap"] is True

    def test_multi_value_flag(self):
        from services.command_diff import _parse_command_to_dict

        args = ["llama-server", "--spec-replace", "target", "draft"]
        result = _parse_command_to_dict(args)
        assert isinstance(result["--spec-replace"], list)
        assert result["--spec-replace"] == ["target", "draft"]

    def test_mixed_flags_and_values(self):
        from services.command_diff import _parse_command_to_dict

        args = [
            "llama-server",
            "-m",
            "model.gguf",
            "--mmap",
            "-c",
            "4096",
            "--threads",
            "8",
        ]
        result = _parse_command_to_dict(args)
        assert result["-m"] == "model.gguf"
        assert result["--mmap"] is True
        assert result["-c"] == "4096"
        assert result["--threads"] == "8"


class TestDiffBooleanFlags:
    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_boolean_flag_added(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.side_effect = [
            ["llama-server", "-m", "model.gguf"],
            ["llama-server", "-m", "model.gguf", "--mmap"],
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert len(result["added"]) == 1
        assert result["added"][0]["flag"] == "--mmap"
        assert result["added"][0]["value"] is None

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_boolean_flag_removed(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.side_effect = [
            ["llama-server", "-m", "model.gguf", "--mmap"],
            ["llama-server", "-m", "model.gguf"],
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert len(result["removed"]) == 1
        assert result["removed"][0]["flag"] == "--mmap"
        assert result["removed"][0]["value"] is None

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_boolean_changed_to_value(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.side_effect = [
            ["llama-server", "-m", "model.gguf", "--threads", "4"],
            ["llama-server", "-m", "model.gguf", "--threads", "8"],
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert len(result["changed"]) == 1
        assert result["changed"][0]["old_value"] == "4"
        assert result["changed"][0]["new_value"] == "8"


class TestDiffEdgeCases:
    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_both_versions_none(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.return_value = ["llama-server", "-m", "model.gguf"]
        mock_version.return_value = None

        result = diff_commands(1, 2)
        assert result["version_1"]["version_number"] == "?"
        assert result["version_2"]["version_number"] == "?"

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_no_differences_empty_lists(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.return_value = [
            "llama-server",
            "-m",
            "model.gguf",
            "-c",
            "4096",
            "--threads",
            "8",
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert result["added"] == []
        assert result["removed"] == []
        assert result["changed"] == []


class TestDiffCommands:
    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_identical_commands(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.return_value = [
            "llama-server",
            "-m",
            "model.gguf",
            "-c",
            "4096",
            "--threads",
            "8",
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert result["added"] == []
        assert result["removed"] == []
        assert result["changed"] == []

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_added_flags(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.side_effect = [
            ["llama-server", "-m", "model.gguf", "-c", "4096"],
            [
                "llama-server",
                "-m",
                "model.gguf",
                "-c",
                "4096",
                "--threads",
                "8",
            ],
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert len(result["added"]) == 1
        assert result["added"][0]["flag"] == "--threads"
        assert result["added"][0]["value"] == "8"
        assert result["removed"] == []
        assert result["changed"] == []

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_removed_flags(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.side_effect = [
            [
                "llama-server",
                "-m",
                "model.gguf",
                "-c",
                "4096",
                "--threads",
                "8",
            ],
            ["llama-server", "-m", "model.gguf", "-c", "4096"],
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert len(result["removed"]) == 1
        assert result["removed"][0]["flag"] == "--threads"
        assert result["removed"][0]["value"] == "8"
        assert result["added"] == []
        assert result["changed"] == []

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_changed_flags(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.side_effect = [
            ["llama-server", "-m", "model.gguf", "-c", "4096"],
            ["llama-server", "-m", "model.gguf", "-c", "8192"],
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert len(result["changed"]) == 1
        assert result["changed"][0]["flag"] == "-c"
        assert result["changed"][0]["old_value"] == "4096"
        assert result["changed"][0]["new_value"] == "8192"
        assert result["added"] == []
        assert result["removed"] == []

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_mixed_diff(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.side_effect = [
            [
                "llama-server",
                "-m",
                "model.gguf",
                "-c",
                "4096",
                "--threads",
                "4",
                "--mmap",
            ],
            [
                "llama-server",
                "-m",
                "model.gguf",
                "-c",
                "8192",
                "--threads",
                "8",
                "--flash-attn",
            ],
        ]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert len(result["added"]) == 1
        assert result["added"][0]["flag"] == "--flash-attn"
        assert len(result["removed"]) == 1
        assert result["removed"][0]["flag"] == "--mmap"
        assert len(result["changed"]) == 2
        changed_flags = [c["flag"] for c in result["changed"]]
        assert "-c" in changed_flags
        assert "--threads" in changed_flags

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_version_info_included(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.return_value = ["llama-server", "-m", "model.gguf"]

        mock_version.side_effect = [
            {"version_number": 3, "config_name": "Alpha"},
            {"version_number": 5, "config_name": "Beta"},
        ]

        result = diff_commands(1, 2)
        assert result["version_1"]["id"] == 1
        assert result["version_1"]["version_number"] == 3
        assert result["version_1"]["config_name"] == "Alpha"
        assert result["version_2"]["id"] == 2
        assert result["version_2"]["version_number"] == 5
        assert result["version_2"]["config_name"] == "Beta"

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_version_not_found(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.return_value = ["llama-server", "-m", "model.gguf"]
        mock_version.return_value = None

        result = diff_commands(1, 2)
        assert result["version_1"]["version_number"] == "?"
        assert result["version_1"]["config_name"] == "?"

    @patch("models.configs.get_version")
    @patch("services.command_diff.build_command")
    def test_command_strings_included(self, mock_build, mock_version):
        from services.command_diff import diff_commands

        mock_build.return_value = ["llama-server", "-m", "model.gguf"]
        mock_version.return_value = {
            "version_number": 1,
            "config_name": "Test",
        }

        result = diff_commands(1, 2)
        assert "llama-server" in result["command_1"]
        assert "model.gguf" in result["command_1"]
        assert "llama-server" in result["command_2"]
