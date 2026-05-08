from unittest.mock import patch, MagicMock
from models.configs import (
    CATEGORIES,
    COMPLEX_TABLES,
    get_all_configs,
    get_config,
    create_config,
    update_config,
    delete_config,
    get_version,
    get_latest_version,
    delete_version,
    get_all_versions,
    next_version_number,
    create_version,
    duplicate_version,
    save_category,
    get_category,
    save_complex_table,
    get_complex_table,
    get_all_version_data,
    save_performance_metric,
    get_performance_metrics,
    get_common_options,
    is_common_option,
    add_common_option,
    remove_common_option,
    reorder_common_options,
)


class QueueCursor:
    """Cursor that returns different results for each execute call,
    and tracks all executed SQL/params for test assertions."""

    def __init__(self, queue=None, lastrowid=1, rowcount=1):
        self._queue = queue or []
        self._idx = 0
        self.lastrowid = lastrowid
        self.rowcount = rowcount
        self.executed_sql = []
        self.executed_params = []

    def execute(self, sql, params=None):
        self.executed_sql.append(sql)
        self.executed_params.append(params)

    def fetchone(self):
        idx = self._idx
        self._idx += 1
        if idx < len(self._queue):
            result = self._queue[idx]
            return (
                result[0]
                if isinstance(result, list) and result
                else (result if result else None)
            )
        return None

    def fetchall(self):
        idx = self._idx
        self._idx += 1
        if idx < len(self._queue):
            result = self._queue[idx]
            return result if isinstance(result, list) else []
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class TrackingConnection:
    """Connection that reuses a single cursor so tests can inspect it."""

    def __init__(self, queue=None, lastrowid=1, rowcount=1):
        self._cursor = QueueCursor(queue, lastrowid, rowcount)

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def _setup_mock(mock_get_conn, queue=None, lastrowid=1, rowcount=1):
    """Configure a get_conn mock to return a TrackingConnection."""
    mock_get_conn.return_value = TrackingConnection(queue, lastrowid, rowcount)
    return mock_get_conn


def _get_cur(mock_get_conn):
    """Get the tracked cursor from a mock for test assertions."""
    return mock_get_conn.return_value.cursor()


# -- Config CRUD --


class TestGetAllConfigs:
    @patch("models.configs.get_conn")
    def test_returns_all_configs(self, mock_get_conn):
        _setup_mock(
            mock_get_conn,
            queue=[[{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]],
        )
        result = get_all_configs()
        assert len(result) == 2
        assert result[0]["name"] == "Alpha"

    @patch("models.configs.get_conn")
    def test_returns_empty_list(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[[]])
        result = get_all_configs()
        assert result == []


class TestGetConfig:
    @patch("models.configs.get_conn")
    def test_returns_config(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"id": 5, "name": "Test"}])
        result = get_config(5)
        assert result["name"] == "Test"

    @patch("models.configs.get_conn")
    def test_returns_none_when_not_found(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[None])
        result = get_config(999)
        assert result is None


class TestCreateConfig:
    @patch("models.configs.get_conn")
    def test_returns_new_id(self, mock_get_conn):
        _setup_mock(mock_get_conn, lastrowid=7)
        result = create_config("MyConfig", "A description", "/models")
        assert result == 7

    @patch("models.configs.get_conn")
    def test_defaults_empty_description_and_model_dir(self, mock_get_conn):
        _setup_mock(mock_get_conn, lastrowid=1)
        result = create_config("Simple")
        assert result == 1


class TestUpdateConfig:
    @patch("models.configs.get_conn")
    def test_updates_config(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        update_config(3, "NewName", "Updated desc", "/new/path")
        cur = _get_cur(mock_get_conn)
        assert cur.executed_sql[0].startswith("UPDATE configs SET")
        assert cur.executed_params[0] == ("NewName", "Updated desc", "/new/path", 3)

    @patch("models.configs.get_conn")
    def test_defaults_empty_description_and_model_dir(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        update_config(3, "NewName")
        cur = _get_cur(mock_get_conn)
        assert cur.executed_params[0] == ("NewName", "", "", 3)


class TestDeleteConfig:
    @patch("models.configs.get_conn")
    def test_deletes_config(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        delete_config(5)
        cur = _get_cur(mock_get_conn)
        assert cur.executed_sql[0].startswith("DELETE FROM configs")
        assert cur.executed_params[0] == (5,)


# -- Version queries --


class TestGetVersion:
    @patch("models.configs.get_conn")
    def test_returns_version_with_config_name(self, mock_get_conn):
        _setup_mock(
            mock_get_conn, queue=[{"id": 10, "config_id": 2, "config_name": "Alpha"}]
        )
        result = get_version(10)
        assert result["config_name"] == "Alpha"

    @patch("models.configs.get_conn")
    def test_returns_none_when_not_found(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[None])
        result = get_version(999)
        assert result is None


class TestGetLatestVersion:
    @patch("models.configs.get_conn")
    def test_returns_latest_version(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"id": 20, "version_number": 5}])
        result = get_latest_version(3)
        assert result["version_number"] == 5


class TestDeleteVersion:
    @patch("models.configs.get_conn")
    def test_returns_true_when_deleted(self, mock_get_conn):
        _setup_mock(mock_get_conn, rowcount=1)
        result = delete_version(10)
        assert result is True

    @patch("models.configs.get_conn")
    def test_returns_false_when_not_found(self, mock_get_conn):
        _setup_mock(mock_get_conn, rowcount=0)
        result = delete_version(999)
        assert result is False


class TestGetAllVersions:
    @patch("models.configs.get_conn")
    def test_returns_versions_desc(self, mock_get_conn):
        _setup_mock(
            mock_get_conn,
            queue=[
                [
                    {"id": 3, "version_number": 3},
                    {"id": 2, "version_number": 2},
                    {"id": 1, "version_number": 1},
                ]
            ],
        )
        result = get_all_versions(1)
        assert len(result) == 3
        assert result[0]["version_number"] == 3

    @patch("models.configs.get_conn")
    def test_returns_empty_list(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[[]])
        result = get_all_versions(1)
        assert result == []


# -- Version creation --


class TestNextVersionNumber:
    @patch("models.configs.get_conn")
    def test_first_version(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"COALESCE(MAX(version_number), 0) + 1": 1}])
        result = next_version_number(1)
        assert result == 1

    @patch("models.configs.get_conn")
    def test_subsequent_version(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"COALESCE(MAX(version_number), 0) + 1": 5}])
        result = next_version_number(1)
        assert result == 5


class TestCreateVersion:
    @patch("models.configs.get_conn")
    @patch("models.configs.next_version_number")
    def test_creates_version_with_next_number(self, mock_next, mock_get_conn):
        mock_next.return_value = 3
        _setup_mock(mock_get_conn, lastrowid=15)
        result = create_version(2, "test comments")
        assert result == 15
        mock_next.assert_called_once_with(2)

    @patch("models.configs.get_conn")
    @patch("models.configs.next_version_number")
    def test_defaults_empty_comments(self, mock_next, mock_get_conn):
        mock_next.return_value = 1
        _setup_mock(mock_get_conn, lastrowid=1)
        result = create_version(5)
        assert result == 1


# -- Duplicate version --


class TestDuplicateVersion:
    @patch("models.configs.get_conn")
    @patch("models.configs.create_version")
    def test_copies_all_categories(self, mock_create, mock_get_conn):
        mock_create.return_value = 20

        cat_row = {"version_id": 1, "ctx_size": 4096, "threads": 8}
        queue = []
        for _ in CATEGORIES:
            queue.append([cat_row])
        for _ in COMPLEX_TABLES:
            queue.append([])

        _setup_mock(mock_get_conn, queue=queue, lastrowid=20)
        result = duplicate_version(1, 5, "dup")
        assert result == 20

        cur = _get_cur(mock_get_conn)
        inserts = [s for s in cur.executed_sql if s.startswith("INSERT")]
        assert len(inserts) >= len(CATEGORIES)

    @patch("models.configs.get_conn")
    @patch("models.configs.create_version")
    def test_copies_complex_tables(self, mock_create, mock_get_conn):
        mock_create.return_value = 25

        lora_rows = [
            {"id": 1, "version_id": 1, "path": "/lora/a.gguf", "scale": 0.5},
            {"id": 2, "version_id": 1, "path": "/lora/b.gguf", "scale": 0.8},
        ]
        queue = []
        for _ in CATEGORIES:
            queue.append([])
        for i in range(6):
            queue.append(lora_rows if i == 0 else [])

        _setup_mock(mock_get_conn, queue=queue)
        duplicate_version(1, 3)

    @patch("models.configs.get_conn")
    @patch("models.configs.create_version")
    def test_skips_empty_categories(self, mock_create, mock_get_conn):
        mock_create.return_value = 30

        queue = []
        for _ in CATEGORIES:
            queue.append([])
        for _ in COMPLEX_TABLES:
            queue.append([])

        _setup_mock(mock_get_conn, queue=queue, lastrowid=30)
        result = duplicate_version(1, 2)
        assert result == 30


# -- Category save/get --


class TestSaveCategory:
    @patch("models.configs.get_conn")
    def test_inserts_new_row(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[None])
        save_category(10, "model_loading", {"model_path": "/models/new.gguf"})
        cur = _get_cur(mock_get_conn)
        assert any("INSERT INTO" in s for s in cur.executed_sql)

    @patch("models.configs.get_conn")
    def test_updates_existing_row(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"version_id": 10}])
        save_category(10, "sampling", {"temperature": 0.9})
        cur = _get_cur(mock_get_conn)
        assert any("UPDATE" in s for s in cur.executed_sql)

    @patch("models.configs.get_conn")
    def test_filters_to_allowed_columns(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[None])
        save_category(10, "sampling", {"temperature": 0.9, "invalid_col": "x"})
        cur = _get_cur(mock_get_conn)
        assert "invalid_col" not in " ".join(cur.executed_sql)

    @patch("models.configs.get_conn")
    def test_uses_correct_table_name(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[None])
        save_category(10, "model_loading", {"ctx_size": 2048})
        cur = _get_cur(mock_get_conn)
        assert "v_model_loading" in cur.executed_sql[0]


class TestGetCategory:
    @patch("models.configs.get_conn")
    def test_returns_category_data(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"ctx_size": 4096, "threads": 8}])
        result = get_category(5, "context_batching")
        assert result["ctx_size"] == 4096

    @patch("models.configs.get_conn")
    def test_returns_empty_dict_when_not_found(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[None])
        result = get_category(5, "sampling")
        assert result == {}


# -- Complex table save/get --


class TestSaveComplexTable:
    @patch("models.configs.get_conn")
    def test_deletes_then_inserts(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        save_complex_table(10, "logit_biases", [{"token_id": 1, "bias_value": 0.5}])
        cur = _get_cur(mock_get_conn)
        sqls = cur.executed_sql
        assert any("DELETE FROM" in s for s in sqls)
        assert any("INSERT INTO" in s for s in sqls)

    @patch("models.configs.get_conn")
    def test_filters_to_allowed_columns(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        save_complex_table(
            10, "logit_biases", [{"token_id": 1, "bias_value": 0.5, "extra": "nope"}]
        )
        cur = _get_cur(mock_get_conn)
        assert "extra" not in " ".join(cur.executed_sql)

    @patch("models.configs.get_conn")
    def test_skips_empty_rows(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        save_complex_table(
            10,
            "logit_biases",
            [
                {"token_id": 1, "bias_value": 0.5},
                {"token_id": 2, "bias_value": 0},
            ],
        )
        cur = _get_cur(mock_get_conn)
        inserts = [s for s in cur.executed_sql if "INSERT" in s]
        assert len(inserts) == 2

    @patch("models.configs.get_conn")
    def test_uses_correct_table_name(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        save_complex_table(10, "lora_adapters", [{"path": "/a.gguf", "scale": 1}])
        cur = _get_cur(mock_get_conn)
        assert "v_lora_adapters" in cur.executed_sql[0]


class TestGetComplexTable:
    @patch("models.configs.get_conn")
    def test_returns_ordered_rows(self, mock_get_conn):
        _setup_mock(
            mock_get_conn,
            queue=[
                [
                    {"id": 1, "token_id": 1, "bias_value": 0.5},
                    {"id": 2, "token_id": 2, "bias_value": -1.0},
                ]
            ],
        )
        result = get_complex_table(5, "logit_biases")
        assert len(result) == 2
        assert result[0]["token_id"] == 1

    @patch("models.configs.get_conn")
    def test_returns_empty_list(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[[]])
        result = get_complex_table(5, "lora_adapters")
        assert result == []


# -- Get all version data --


class TestGetAllVersionData:
    @patch("models.configs.get_category")
    @patch("models.configs.get_complex_table")
    def test_returns_all_categories_and_complex(self, mock_complex, mock_cat):
        mock_cat.return_value = {}
        mock_complex.return_value = []

        result = get_all_version_data(1)
        for cat in CATEGORIES:
            assert cat in result
        for tbl in COMPLEX_TABLES:
            assert tbl in result
        assert len(result) == len(CATEGORIES) + len(COMPLEX_TABLES)

    @patch("models.configs.get_category")
    @patch("models.configs.get_complex_table")
    def test_calls_get_category_for_each_category(self, mock_complex, mock_cat):
        mock_cat.return_value = {"x": 1}
        mock_complex.return_value = []
        get_all_version_data(5)
        assert mock_cat.call_count == len(CATEGORIES)

    @patch("models.configs.get_category")
    @patch("models.configs.get_complex_table")
    def test_calls_get_complex_table_for_each_table(self, mock_complex, mock_cat):
        mock_cat.return_value = {}
        mock_complex.return_value = [{"a": 1}]
        get_all_version_data(5)
        assert mock_complex.call_count == len(COMPLEX_TABLES)


# -- Performance metrics --


class TestSavePerformanceMetric:
    @patch("models.configs.get_conn")
    def test_returns_new_id(self, mock_get_conn):
        _setup_mock(mock_get_conn, lastrowid=42)
        result = save_performance_metric(
            10, load_time=5.2, tps=30.0, vram_used=4096, peak_cpu=80.0, notes="fast"
        )
        assert result == 42

    @patch("models.configs.get_conn")
    def test_accepts_none_values(self, mock_get_conn):
        _setup_mock(mock_get_conn, lastrowid=1)
        result = save_performance_metric(10)
        assert result == 1


class TestGetPerformanceMetrics:
    @patch("models.configs.get_conn")
    def test_returns_metrics_desc(self, mock_get_conn):
        _setup_mock(
            mock_get_conn,
            queue=[
                [
                    {"id": 1, "tps": 30.0},
                    {"id": 2, "tps": 28.0},
                ]
            ],
        )
        result = get_performance_metrics(10)
        assert len(result) == 2
        assert result[0]["tps"] == 30.0

    @patch("models.configs.get_conn")
    def test_returns_empty_list(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[[]])
        result = get_performance_metrics(10)
        assert result == []


# -- Common options --


class TestGetCommonOptions:
    @patch("models.configs.get_conn")
    def test_returns_ordered_options(self, mock_get_conn):
        _setup_mock(
            mock_get_conn,
            queue=[
                [
                    {
                        "id": 1,
                        "display_order": 0,
                        "category": "sampling",
                        "column_name": "temperature",
                    },
                    {
                        "id": 2,
                        "display_order": 1,
                        "category": "memory",
                        "column_name": "mmap",
                    },
                ]
            ],
        )
        result = get_common_options()
        assert len(result) == 2
        assert result[0]["display_order"] == 0

    @patch("models.configs.get_conn")
    def test_returns_empty_list(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[[]])
        result = get_common_options()
        assert result == []


class TestIsCommonOption:
    @patch("models.configs.get_conn")
    def test_returns_true_when_exists(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"id": 1}])
        result = is_common_option("sampling", "temperature")
        assert result is True

    @patch("models.configs.get_conn")
    def test_returns_false_when_not_found(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[None])
        result = is_common_option("sampling", "nonexistent")
        assert result is False


class TestAddCommonOption:
    @patch("models.configs.get_conn")
    def test_returns_true_on_success(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"max_order": 5}])
        result = add_common_option("memory", "mmap", "Memory Map")
        assert result is True

    @patch("models.configs.get_conn")
    def test_starts_at_order_zero(self, mock_get_conn):
        _setup_mock(mock_get_conn, queue=[{"max_order": None}])
        add_common_option("sampling", "temperature")
        cur = _get_cur(mock_get_conn)
        assert cur.executed_params[1][2] == 1

    @patch("models.configs.get_conn")
    def test_returns_false_on_duplicate(self, mock_get_conn):
        mock_conn_val = mock_get_conn.return_value
        mock_conn_val.__enter__ = lambda s: s
        mock_conn_val.__exit__ = lambda s, *a: None

        mock_cur = MagicMock()
        mock_cur.__enter__ = lambda s: s
        mock_cur.__exit__ = lambda s, *a: None
        mock_cur.fetchone.return_value = {"max_order": 3}
        mock_cur.execute.side_effect = [None, Exception("Duplicate entry")]

        mock_conn_val.cursor.return_value = mock_cur
        result = add_common_option("sampling", "temperature")
        assert result is False


class TestRemoveCommonOption:
    @patch("models.configs.get_conn")
    def test_returns_true_when_deleted(self, mock_get_conn):
        _setup_mock(mock_get_conn, rowcount=1)
        result = remove_common_option(5)
        assert result is True

    @patch("models.configs.get_conn")
    def test_returns_false_when_not_found(self, mock_get_conn):
        _setup_mock(mock_get_conn, rowcount=0)
        result = remove_common_option(999)
        assert result is False


class TestReorderCommonOptions:
    @patch("models.configs.get_conn")
    def test_updates_display_order(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        reorder_common_options([3, 1, 2])
        cur = _get_cur(mock_get_conn)
        assert len(cur.executed_sql) == 3
        assert cur.executed_params[0] == (0, 3)
        assert cur.executed_params[1] == (1, 1)
        assert cur.executed_params[2] == (2, 2)

    @patch("models.configs.get_conn")
    def test_empty_list_no_updates(self, mock_get_conn):
        _setup_mock(mock_get_conn)
        reorder_common_options([])
        cur = _get_cur(mock_get_conn)
        assert len(cur.executed_sql) == 0
