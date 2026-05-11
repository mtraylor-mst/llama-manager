# Setup & Installation

This guide will walk you through setting up `llama-manager` on your system.

## Prerequisites

Before installing `llama-manager`, ensure you have the following components installed and configured.

### 1. Python
`llama-manager` requires Python 3.10 or higher.
- **Linux/macOS**: Most modern distributions come with Python. You can check your version with `python3 --version`.
- **Recommendation**: It is highly recommended to use a virtual environment (e.g., `venv` or `conda`) to avoid conflicts with system packages.

### 2. Database (MySQL or MariaDB)
The application uses a MySQL/MariaDB backend to store configurations, versions, and performance metrics.
- **Installation**: Install via your package manager (e.g., `sudo apt install mariadb-server` on Ubuntu or `brew install mariadb` on macOS).
- **Setup**: You will need to create a database named `llama_configs` and a user with appropriate permissions.

### 3. llama.cpp Server
`llama-manager` is a management layer for the `llama.cpp` server. You must have the `llama-server` binary available on your system path or know its absolute location.
- **Build from source**: Follow the instructions in the [official llama.cpp repository](https://github.com/ggerganov/llama.cpp).

---

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd llama-manager
```

### 2. Install Dependencies
It is recommended to use a virtual environment (created via `uv`):
```bash
# Create and activate a virtual environment
uv venv --python 3.10 --seed
source .venv/bin/activate  # On macOS/Linux

# Install required Python packages
pip install -r requirements.txt
```

### 3. Initialize the Database
Run the provided schema against your MySQL/MariaDB instance to create the necessary tables. Replace `$HOST`, `$USER`, and `$PASSWORD` with your actual database credentials.

```bash
mysql -h $HOST -u $USER -p llama_configs < schema.sql
```

---

## Configuration

`llama-manager` is configured primarily through environment variables. You can set these in your shell or via a `.env` file (loaded automatically by `python-dotenv`).

| Variable | Default | Description |
|---|---|---|
| `LLAMA_DB_HOST` | `127.0.0.1` | Database host |
| `LLAMA_DB_USER` | `username` | Database user |
| `LLAMA_DB_PASS` | `password` | Database password |
| `LLAMA_DB_NAME` | `llama_configs` | Database name |
| `LLAMA_MODEL_DIR` | `/home/mtraylor/.cache/huggingface/hub/` | Default directory for GGUF models |
| `LLAMA_SERVER_BINARY` | `/usr/local/bin/llama-server` | Path to the `llama-server` binary |
| `LLAMA_SECRET_KEY` | *(random)* | Flask secret key for secure sessions |
| `AUTH_ENABLED` | `false` | Enable HTTP Basic Auth |
| `AUTH_USER` | | Auth username |
| `AUTH_PASSWORD` | | Auth password |
| `DEBUG` | `false` | Flask debug mode |

---

## Running the Application

Once setup is complete, you can start the manager using:

```bash
python run.py
```

The interface will be available at `http://127.0.0.1:8081`.
