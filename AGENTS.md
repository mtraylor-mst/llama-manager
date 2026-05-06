# AGENTS.md — Coding Guidelines for llama-manager

## Project Overview

llama-manager is a Flask web application that tracks, compares, and launches [llama.cpp](https://github.com/ggerganov/llama.cpp) server configurations. It uses HTMX for partial page updates, PyMySQL for database access, and subprocess management with PID tracking for running llama-server processes.

## Tech Stack

- **Framework**: Flask 3.x
- **Frontend**: Jinja2 templates + HTMX (no SPA framework)
- **Database**: MySQL/MariaDB via PyMySQL
- **Forms**: Flask-WTF / WTForms
- **Testing**: pytest
- **Linting/Formatting**: ruff

## Project Structure

```
llama-manager/
├── app.py              # Flask factory, blueprint registration, middleware
├── run.py              # Entry point (load_dotenv → create_app → run)
├── config.py           # Environment-based configuration
├── template_utils.py   # Jinja2 template helpers/filters
├── schema.sql          # Database schema
├── requirements.txt    # Dependencies
├── routes/             # Flask blueprints (one per domain)
│   ├── configs.py      # Config CRUD, import logic
│   ├── versions.py     # Version management, fork/duplicate
│   ├── server.py       # Launch/stop, live logs via SSE
│   ├── api.py          # JSON API endpoints
│   └── common.py       # Shared routes (nav, etc.)
├── models/             # Database access layer
│   └── configs.py      # All SQL queries for configs/versions
├── services/           # Business logic
│   ├── command_builder.py    # llama-server CLI construction
│   ├── config_importer.py    # Parse running server into config
│   ├── screen_manager.py     # subprocess lifecycle + PID tracking
│   └── benchmarks.py         # TPS benchmarking logic
├── utils/              # Cross-cutting utilities
│   └── rate_limit.py   # Rate limiting decorator
├── templates/          # Jinja2 HTML templates
├── static/             # CSS, JS assets
└── tests/              # pytest test suite
```

## Conventions

### Code Style

- Use `ruff` for linting and formatting. Run `ruff check .` and `ruff format .` before committing.
- Follow PEP 8 with standard Python naming conventions.
- No emojis in code or documentation unless explicitly requested.

### Database Access

- All database queries go through `models/base.py` (`get_conn()`) for connection pooling.
- Use parameterized queries exclusively — never string-format SQL.
- New tables/columns require updates to `schema.sql`.

### Routes & Blueprints

- Each domain area gets its own blueprint in `routes/`.
- Keep route handlers thin; delegate business logic to `services/`.
- Use HTMX partial responses (`HX-Trigger`, `HX-Redirect`) for async interactions.

### Process Management

- llama-server is launched via `subprocess.Popen` in `services/screen_manager.py`.
- Uses a PID file (`/tmp/.llama-manager.pid`) for process recovery across app restarts.
- Fallback discovery via `lsof` on log files and `pgrep` by process name.
- Stop sends SIGTERM, waits up to 5s, then SIGKILL if needed. Always cleans up the PID file.

### Secrets & Configuration

- Never hardcode secrets — use environment variables through `.env`.
- Sensitive values (DB credentials, API keys) must be redacted in logs and command previews.

## Development Workflow

### Running Locally

Install .venv through uv, then activate the .venv before running any python commands

```bash
uv venv --python 3.10 --seed
source .venv/bin/activate
```

Once you're in a venv, run the rest of the installation

```bash
pip install -r requirements.txt
mysql -h $HOST -u $USER -p llama_configs < schema.sql
python run.py
# App runs on http://0.0.0.0:8081
```

### Testing

```bash
pytest tests/           # Run all tests
pytest tests/test_foo.py  # Run specific test file
```

Tests use mocked database connections (`MockCursor`/`MockConnection` in `conftest.py`). No real database is needed for the test suite.

### CI

GitHub Actions runs `pytest tests/` on every push. Ensure tests pass locally before pushing.

## Adding Features

1. **New route**: Create or extend a blueprint in `routes/`, register in `app.py`.
2. **New model query**: Add function to `models/configs.py`, use parameterized SQL.
3. **New service logic**: Place in `services/`, keep it stateless where possible.
4. **Template changes**: Follow existing HTMX patterns; partial templates go in their respective subdirectories.
5. **Always add tests** for new functionality.
