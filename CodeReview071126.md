# Code Review Checklist — 2026-07-11

## High Severity

- [x] **`models/base.py:57-62`** — ~~`PooledConnection.__exit__` auto-commits/rollbacks...~~ **Fixed.** Removed implicit commit/rollback from `__exit__`; all callers already manage their own transaction lifecycle.
- [x] **`routes/versions.py:252-341`** — ~~`_edit_form` is a 90-line god function...~~ **Fixed.** Extracted `copy_version_data()` into `models/configs.py`. Fork path in `_edit_form` now delegates to `duplicate_version()` + `_save_version_data()`, eliminating 36 lines of duplicated SQL. Moved `duplicate_version`/`get_all_version_data` to module-level imports for testability.
- [x] **`routes/versions.py:182-249`** — ~~`_save_version_data` (68 lines) mixed concerns...~~ **Fixed.** Extracted four focused helpers: `_update_version_metadata()`, `_convert_field_value()`, `_parse_category_data()`, `_parse_complex_table_rows()`. The orchestrator `_save_version_data` is now 15 lines.

## Medium Severity

- [x] **`app.py:45-61`** — ~~`inject_context` runs expensive process discovery...~~ **Fixed.** Added `_find_running_cached()` with 2s TTL in `screen_manager.py`. Cache invalidated on start/stop. Both `get_status()` and `get_running_version_id()` use the cached path.
- [x] ~~Running-version detection logic duplicated across 3 files...~~ **Fixed.** Added `get_running_for_config(config_id, versions)` in `screen_manager.py`. Updated all 3 call sites in `configs.py` and `versions.py` to use it.
- [x] **`services/config_importer.py:559-561`** — ~~`_compare_signatures` skips `val == 0`...~~ **Fixed.** Removed `val == 0` from skip condition. Added tests for zero-vs-nonzero mismatch, zero-vs-zero match, and None/empty skipping.
- [x] **`services/command_builder.py:476-489`** — ~~Hardcoded category list...~~ **Fixed.** Replaced 13-line hardcoded list with `from models.configs import CATEGORIES`.
- [x] **`services/command_diff.py:15`** — ~~Dead code (`pass`) and buggy multi-value...~~ **Fixed.** Removed dead `if current_flag: pass`. Fixed multi-value handling to properly accumulate values in a list instead of string-concatenating (which produced `"True some_arg"` for boolean flags).
- [x] **`services/command_builder.py:12-16`** — ~~`float_fmt` had confusing/unreachable logic...~~ **Fixed.** Simplified to always return `f"{v:f}".rstrip("0").rstrip(".")`. The `else f"{v:.4f}"` branch was unreachable (condition was always True).
- [x] **`routes/versions.py:26-80`** — ~~Near-duplicate functions...~~ **Fixed.** Extracted `_resolve_option_label()` and `_option_to_dict()` helpers. Both `get_common_options_list` and `get_common_options_grouped` now share label resolution and dict construction logic.
- [ ] ~~**`services/vram_stress_test.py:315-472`** — 159-line `_execute_stress_test` with deeply nested lifecycle, phases, and metrics. Extract phases.~~ *(deprioritized — incomplete feature)*
- [x] **`routes/common.py:40`** — ~~Cross-route import...~~ **Fixed.** Moved `CATEGORY_LABELS` to `template_utils.py` (where `CATEGORY_FIELDS`, `COMPLEX_LABELS` already live). Both `routes/versions.py` and `routes/common.py` now import from `template_utils`.

## Low Severity

- [x] **`utils/rate_limit.py:13`** — ~~`_calls` dict grows unbounded...~~ **Fixed.** Keys with empty timestamp lists are now deleted during pruning to prevent unbounded growth.
- [x] ~~`get_all_configs` return type defensive code...~~ **Fixed.** Removed unnecessary `isinstance(latest, dict) else latest[0]` in `config_importer.py:631` — `DictCursor` always returns dicts. (The other instance in `configs.py` was already removed during #5.)
- [x] ~~`pooling_override` column exists...~~ **Fixed.** Removed from `CATEGORY_COLUMNS` (no corresponding CLI flag in llama.cpp). DB column left as-is (harmless nullable VARCHAR).
- [x] ~~`_normalize_flag` and `--no-` prefix handling...~~ **Fixed.** Extracted `_parse_no_flag()` to handle `--no-xxx` flags consistently with a clear docstring.
- [x] ~~`neg_bool` helper is dead code...~~ **Fixed.** Removed `neg_bool` function and its reference in `FLAG_DEFINITIONS`. Removed corresponding test class.

## Testing Gaps

- [x] **`template_utils.py`** — ~~`render_field()` had zero tests...~~ **Fixed.** Added 6 new tests (31 total in file): tristate with Python booleans, select with string options, float field, password with HTML special chars, unknown category fallback. Existing tests already covered bool/tristate/select/password/complex well.
- [x] **`model_parser.py`** — ~~No tests for log parsing regexes...~~ **Fixed.** Added 12 new tests (27 total in file): `_parse_size_to_bytes` direct tests, `_get_ctx_from_log`, memory breakdown derived fields (`ctx_per_token_mb`, `est_max_ctx_tokens`), and regex edge cases (extra whitespace, string values, BPW parenthesis).
- [x] **`command_diff.py`** — ~~No unit tests...~~ **Fixed.** Added 9 new tests (21 total in file): consecutive boolean flags, flag at end without value, multi-value flag accumulation, mixed flags/values, boolean flag add/remove/change in diffs, both versions None edge case.
- [x] **`vram_safety.py`** — ~~No tests for estimates...~~ **Fixed.** Added 7 new tests (31 total in file): q4_0 quantization calculation, n_head_kv fallback to n_head, negative compaction coefficient fallback, missing/zero required fields in empirical, exact color threshold boundaries.
- [ ] ~~**`vram_stress_test.py`** (603 lines) — Zero tests.~~ *(deprioritized — incomplete feature)*
