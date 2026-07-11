# Code Review Checklist — 2026-07-11

## High Severity

- [x] **`models/base.py:57-62`** — ~~`PooledConnection.__exit__` auto-commits/rollbacks...~~ **Fixed.** Removed implicit commit/rollback from `__exit__`; all callers already manage their own transaction lifecycle.
- [x] **`routes/versions.py:252-341`** — ~~`_edit_form` is a 90-line god function...~~ **Fixed.** Extracted `copy_version_data()` into `models/configs.py`. Fork path in `_edit_form` now delegates to `duplicate_version()` + `_save_version_data()`, eliminating 36 lines of duplicated SQL. Moved `duplicate_version`/`get_all_version_data` to module-level imports for testability.
- [x] **`routes/versions.py:182-249`** — ~~`_save_version_data` (68 lines) mixed concerns...~~ **Fixed.** Extracted four focused helpers: `_update_version_metadata()`, `_convert_field_value()`, `_parse_category_data()`, `_parse_complex_table_rows()`. The orchestrator `_save_version_data` is now 15 lines.

## Medium Severity

- [x] **`app.py:45-61`** — ~~`inject_context` runs expensive process discovery...~~ **Fixed.** Added `_find_running_cached()` with 2s TTL in `screen_manager.py`. Cache invalidated on start/stop. Both `get_status()` and `get_running_version_id()` use the cached path.
- [x] ~~Running-version detection logic duplicated across 3 files...~~ **Fixed.** Added `get_running_for_config(config_id, versions)` in `screen_manager.py`. Updated all 3 call sites in `configs.py` and `versions.py` to use it.
- [ ] **`services/config_importer.py:559-561`** — `_compare_signatures` skips `val == 0`, causing false signature matches (e.g., `mirostat=0` matches `mirostat=2`).
- [ ] **`services/command_builder.py:476-489`** — Hardcoded category list instead of importing shared `CATEGORIES` constant.
- [ ] **`services/command_diff.py:15`** — Dead code (`pass`) and buggy multi-value flag concatenation in `_parse_command_to_dict`.
- [ ] **`services/command_builder.py:12-16`** — `float_fmt` has confusing/unreachable logic producing `"0.0000"` for integer inputs.
- [ ] **`routes/versions.py:26-80`** — Near-duplicate functions `get_common_options_list` / `get_common_options_grouped`. Extract shared label resolution.
- [ ] ~~**`services/vram_stress_test.py:315-472`** — 159-line `_execute_stress_test` with deeply nested lifecycle, phases, and metrics. Extract phases.~~ *(deprioritized — incomplete feature)*
- [ ] **`routes/common.py:40`** — Cross-route import (`from routes.versions import CATEGORY_LABELS`) creates circular-dependency risk. Move to shared constants.

## Low Severity

- [ ] **`utils/rate_limit.py:13`** — `_calls` dict grows unbounded (keys never deleted).
- [ ] `get_all_configs` return type defensive code (`isinstance(v, dict) else v[0]`) is unnecessary with `DictCursor`. Clean up or add explanatory comment.
- [ ] `pooling_override` column exists in `advanced` category but has no flag mapping in `command_builder.py`. Either add the mapping or remove the column.
- [ ] `_normalize_flag` and `--no-` prefix handling are fragile across two code paths in `config_importer.py`. Consolidate normalization.
- [ ] `neg_bool` helper in `command_builder.py` is dead code — never wired into command building. Remove or wire it in.

## Testing Gaps

- [ ] **`template_utils.py`** — `render_field()` has zero tests despite handling bool/tristate/select/password/complex rendering.
- [ ] **`model_parser.py`** — No tests for log parsing regexes (`_PRINT_INFO_RE`, `_MEMORY_BREAKDOWN_RE`).
- [ ] **`command_diff.py`** — No unit tests for `_parse_command_to_dict` or `diff_commands`.
- [ ] **`vram_safety.py`** — No tests for `theoretical_estimate` or `empirical_estimate` calculations.
- [ ] ~~**`vram_stress_test.py`** (603 lines) — Zero tests.~~ *(deprioritized — incomplete feature)*
