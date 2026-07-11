# Feature Ideas — llama-manager

## 1. Config Validation Before Launch [DONE]

Currently, errors surface after the process starts and crashes. A pre-launch validation step would check:

- **Model file exists** — filesystem check on `--model` path
- **VRAM fit estimate** — reuse existing `vram_safety.theoretical_estimate()` to warn before launch
- **Required flags** — `model_path` must be set; draft model requires speculative settings
- **Value sanity** — negative/zero values for ctx-size, threads, etc.

**Key constraint:** Must not require restarting llama-server. The existing `vram_safety` module is safe to use because it reads from DB metadata and file stat — no process interaction needed. Avoid any path that triggers `screen_manager.start()`.

**Implementation:** New `services/config_validator.py` with a `validate(version_id) -> list[dict]` function. Integrate into `routes/server.py:start()` as a pre-check, returning warnings/errors before `build_command` + `screen_manager.start()`.

---

## 2. Config Templates / Presets [DONE]

Power users repeatedly tweak the same base config for different models. A "save as template" feature with parameterized fields (model path, n_ctx) would reduce copy-paste drift.

**Scope:** New `config_templates` table. Template rows reference category/column like existing configs, but support `{{variable}}` placeholders. UI to create from existing version, mark fields as templatable, and instantiate new configs from template.

---

## 3. Bulk Operations

No way to stop all running servers at once or batch-import configs from a directory.

**Scope:**
- "Stop All" button in nav (iterates `screen_manager.stop()` for all PIDs)
- "Import Folder" endpoint that reads `.json` or `.sh` files from a directory, parses each into a config

---

## 4. Config Version Diff Visualization [DONE]

`command_diff.py` exists but only returns structured data. A visual HTMX diff view (like GitHub's file compare) between two versions of the same config would make changes obvious at a glance.

**Scope:** New route `/version/<id1>/diff/<id2>` that renders a side-by-side HTML diff using the existing `command_diff.compare_versions()` output. Green/red highlights for added/removed/changed flags.

---

## 5. Server Health Endpoint [DONE]

Beyond PID tracking, an actual `/health` check that pings the llama-server HTTP API to confirm it's responsive, not just alive. Could surface in the nav bar.

**Scope:** New endpoint that `requests.get()`s the llama-server `--host`/`--port` at `/health`. Returns status + response time. Nav badge updates from "● Running" to "● Running (2ms)" or "● Unresponsive".

---

## 6. Config Usage Analytics [DONE]

Track which configs are launched most often, average runtime, common failure modes. Helps identify zombie configs and popular setups worth promoting.

**Scope:** New `config_usage` table (version_id, launched_at, stopped_at, exit_reason). Hooks into `screen_manager.start()`/`stop()`. Dashboard page with top configs, uptime trends, crash frequency.
