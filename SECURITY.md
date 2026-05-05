# Security Review — llama-manager

## Critical

### 1. Hardcoded DB credentials fallback (`config.py:4-7`)
Default `DB_USER` and `DB_PASS` are hardcoded as `'llama_mgr'`. If env vars aren't set, these weak defaults are used.

### 2. Hardcoded Flask secret key (`config.py:19`)
`SECRET_KEY` defaults to `'change-me-in-production'`, making session cookies predictable and allowing session hijacking.

### 3. Debug mode enabled (`run.py:6`)
`debug=True` exposes the interactive debugger, which allows remote code execution.

### 4. No CSRF protection
All POST endpoints across `routes/*.py` lack CSRF tokens. Flask-WTF or manual CSRF is not used anywhere.

### 5. SQL Injection via dynamic table/column names (`models/configs.py:146-171`, `save_category:178-203`, `save_complex_table:214-229`)
Table names are interpolated directly into SQL from constants. Column names derived from user form data (`data.keys()`) at lines 187-195 are also interpolated directly, without validation against a whitelist.

### 6. Command Injection (`services/screen_manager.py:118-124`)
The `command` string (built from user-controlled DB values via `build_command`) is passed unsanitized into `bash -c`, allowing arbitrary command execution through crafted config values like model paths, API keys, etc.

## High

### 7. No authentication/authorization
Every endpoint is publicly accessible with no login required. Anyone reaching port 8081 can create/delete configs, start/stop servers, and execute arbitrary commands.

### 8. XSS in templates (`templates/configs/view.html:20`, `base.html:32`)
User-controlled fields like `featured.comments`, `config.description`, and flash messages are rendered in templates. While Jinja2 auto-escapes by default, flash messages from `routes/server.py:142` embed exception strings directly into HTML responses.

### 9. XSS in HTMX inline responses (`routes/server.py:25-32`, `routes/common.py:66`)
Server-generated HTML fragments don't escape dynamic content like `running_ver_info["config_name"]`.

### 10. Unrestricted file access via `/api/models` (`routes/api.py:9-11`, `services/command_builder.py:607-623`)
The `dir` query parameter allows walking any filesystem directory and enumerating files, enabling path traversal reconnaissance.

## Medium

### 11. Sensitive data in command output API (`routes/versions.py:304-308`)
`/version/<id>/command` returns the full command line including secrets like `--hf-token`, `--api-key`.

### 12. No rate limiting
All endpoints, especially server start/stop and benchmark, can be called repeatedly without throttling.

### 13. Insecure session configuration
No `session_cookie_secure`, `session_cookie_httponly`, or `permanently_redirect` settings are configured on the Flask app.

### 14. Wildcard dependencies (`requirements.txt`)
Unpinned versions (`Flask==3.1.*`) could pull in vulnerable updates.

### 15. Missing `.env` in `.gitignore`
If secrets are stored via environment variables in a `.env` file, it could be accidentally committed.

## Low

### 16. SSE log streaming resource leak (`routes/server.py:80-97`)
`tail -fn10` is spawned per request but never explicitly terminated on client disconnect.

### 17. Verbose error exposure (`routes/common.py:13`, `routes/server.py:142`)
Exception details are returned directly to the client in responses.
