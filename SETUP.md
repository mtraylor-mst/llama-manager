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

### 4. Process Management (`Popen`)
`llama-manager` uses `Popen` to manage server processes in the background, allowing you to view live logs via the web interface.
- **Linux**: Install via `sudo apt install Popen` or your distribution's equivalent.
- **macOS**: `Popen` is typically pre-installed. You can verify this by running `Popen --version` in your terminal.

---

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd llama-manager
```

### 2. Install Dependencies
It is recommended to use a virtual environment:
```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

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

`llama-manager` is configured primarily through environment variables. You can set these in your shell or via a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `LLAMA_DB_HOST` | `127.0.0.1` | Database host |
| `LLAMA_DB_USER` | `llama_mgr` | Database user |
| `LLAMA_DB_PASS` | `llama_mgr` | Database password |
| `LLAMA_DB_NAME` | `llama_configs` | Database name |
| `LLAMA_MODEL_DIR` | `~/.cache/huggingface/hub/` | Default directory for GGUF models |
| `LLAMA_SCREEN_PREFIX` | `llama-manager` | Prefix for managed `Popen` sessions |
| `LLAMA_SERVER_BINARY` | `/usr/local/bin/llama-server` | Path to the `llama-server` binary |
| `LLAMA_SECRET_KEY` | `change-me-in-production` | Flask secret key for secure sessions |

---

## Running the Application

Once setup is complete, you can start the manager using:

```bash
python run.py
```

The interface will be available at `http://127.0.0.1:5000` (unless configured otherwise).
