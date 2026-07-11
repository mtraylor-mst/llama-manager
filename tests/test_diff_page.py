"""Tests for version diff route and template rendering."""

from unittest.mock import patch


class TestDiffRoute:
    @patch("services.command_diff.diff_commands")
    @patch("models.configs.get_version")
    def test_diff_page_renders(self, mock_version, mock_diff, client):
        mock_version.return_value = {
            "id": 1,
            "version_number": 3,
            "config_id": 1,
            "config_name": "Test Config",
            "created_at": None,
            "comments": "Test version",
        }
        mock_diff.return_value = {
            "version_1": {"id": 1, "version_number": 3, "config_name": "Test Config"},
            "version_2": {"id": 2, "version_number": 4, "config_name": "Test Config"},
            "added": [{"flag": "--mmap", "value": None}],
            "removed": [{"flag": "-c", "value": "4096"}],
            "changed": [{"flag": "--threads", "old_value": "4", "new_value": "8"}],
            "command_1": "llama-server -m model.gguf -c 4096",
            "command_2": "llama-server -m model.gguf --mmap",
        }

        resp = client.get("/version/1/diff/2")
        assert resp.status_code == 200
        assert b"Version Diff" in resp.data
        assert b"v3" in resp.data
        assert b"v4" in resp.data
        assert b"--mmap" in resp.data
        assert b"--threads" in resp.data

    @patch("models.configs.get_version")
    def test_diff_missing_version_redirects(self, mock_version, client):
        mock_version.return_value = None
        resp = client.get("/version/999/diff/1", follow_redirects=False)
        assert resp.status_code == 302


class TestDiffPageNoChanges:
    @patch("services.command_diff.diff_commands")
    @patch("models.configs.get_version")
    def test_no_differences_message(self, mock_version, mock_diff, client):
        mock_version.return_value = {
            "id": 1,
            "version_number": 1,
            "config_id": 1,
            "config_name": "Test",
            "created_at": None,
            "comments": "",
        }
        mock_diff.return_value = {
            "version_1": {"id": 1, "version_number": 1, "config_name": "Test"},
            "version_2": {"id": 2, "version_number": 2, "config_name": "Test"},
            "added": [],
            "removed": [],
            "changed": [],
            "command_1": "llama-server -m model.gguf",
            "command_2": "llama-server -m model.gguf",
        }

        resp = client.get("/version/1/diff/2")
        assert resp.status_code == 200
        assert b"No differences" in resp.data


class TestDiffPageBooleanFlags:
    @patch("services.command_diff.diff_commands")
    @patch("models.configs.get_version")
    def test_boolean_flag_displayed(self, mock_version, mock_diff, client):
        """Boolean flags (no value) show '(enabled)' instead of raw None."""
        mock_version.return_value = {
            "id": 1,
            "version_number": 1,
            "config_id": 1,
            "config_name": "Test",
            "created_at": None,
            "comments": "",
        }
        mock_diff.return_value = {
            "version_1": {"id": 1, "version_number": 1, "config_name": "Test"},
            "version_2": {"id": 2, "version_number": 2, "config_name": "Test"},
            "added": [{"flag": "--mmap", "value": None}],
            "removed": [],
            "changed": [],
            "command_1": "llama-server -m model.gguf",
            "command_2": "llama-server -m model.gguf --mmap",
        }

        resp = client.get("/version/1/diff/2")
        assert resp.status_code == 200
        assert b"(enabled)" in resp.data


class TestDiffPageChangedFlags:
    @patch("services.command_diff.diff_commands")
    @patch("models.configs.get_version")
    def test_changed_flag_shows_old_and_new(self, mock_version, mock_diff, client):
        """Changed flags show old value (strikethrough) and new value (bold)."""
        mock_version.return_value = {
            "id": 1,
            "version_number": 1,
            "config_id": 1,
            "config_name": "Test",
            "created_at": None,
            "comments": "",
        }
        mock_diff.return_value = {
            "version_1": {"id": 1, "version_number": 1, "config_name": "Test"},
            "version_2": {"id": 2, "version_number": 2, "config_name": "Test"},
            "added": [],
            "removed": [],
            "changed": [{"flag": "-c", "old_value": "4096", "new_value": "8192"}],
            "command_1": "llama-server -m model.gguf -c 4096",
            "command_2": "llama-server -m model.gguf -c 8192",
        }

        resp = client.get("/version/1/diff/2")
        assert resp.status_code == 200
        assert b"4096" in resp.data
        assert b"8192" in resp.data
        assert b"diff-removed-cell" in resp.data
        assert b"diff-added-cell" in resp.data


class TestDiffSummaryCounts:
    @patch("services.command_diff.diff_commands")
    @patch("models.configs.get_version")
    def test_summary_shows_counts(self, mock_version, mock_diff, client):
        """Summary bar shows correct counts for each change type."""
        mock_version.return_value = {
            "id": 1,
            "version_number": 1,
            "config_id": 1,
            "config_name": "Test",
            "created_at": None,
            "comments": "",
        }
        mock_diff.return_value = {
            "version_1": {"id": 1, "version_number": 1, "config_name": "Test"},
            "version_2": {"id": 2, "version_number": 2, "config_name": "Test"},
            "added": [{"flag": "--a", "value": None}, {"flag": "--b", "value": "x"}],
            "removed": [{"flag": "--c", "value": None}],
            "changed": [{"flag": "-t", "old_value": "1", "new_value": "2"}],
            "command_1": "",
            "command_2": "",
        }

        resp = client.get("/version/1/diff/2")
        assert resp.status_code == 200
        assert b"2 added" in resp.data
        assert b"1 removed" in resp.data
        assert b"1 changed" in resp.data


class TestDiffFullCommands:
    @patch("services.command_diff.diff_commands")
    @patch("models.configs.get_version")
    def test_full_commands_in_details(self, mock_version, mock_diff, client):
        """Full commands are available in a collapsible details section."""
        cmd1 = "llama-server -m /models/v1.gguf -c 4096 --threads 4"
        cmd2 = "llama-server -m /models/v2.gguf -c 8192 --threads 8"

        mock_version.return_value = {
            "id": 1,
            "version_number": 1,
            "config_id": 1,
            "config_name": "Test",
            "created_at": None,
            "comments": "",
        }
        mock_diff.return_value = {
            "version_1": {"id": 1, "version_number": 1, "config_name": "Test"},
            "version_2": {"id": 2, "version_number": 2, "config_name": "Test"},
            "added": [],
            "removed": [],
            "changed": [{"flag": "-c", "old_value": "4096", "new_value": "8192"}],
            "command_1": cmd1,
            "command_2": cmd2,
        }

        resp = client.get("/version/1/diff/2")
        assert resp.status_code == 200
        assert b"Full Commands" in resp.data
        assert cmd1.encode() in resp.data
        assert cmd2.encode() in resp.data
