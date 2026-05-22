"""Parse architecture metadata from llama-server log files."""

import os
import re
from models.base import get_conn


_PRINT_INFO_RE = re.compile(
    r"^\s*print_info:\s+(\w+)\s*=\s*(.+)$"
)

_FILE_SIZE_RE = re.compile(
    r"^file size\s*=\s*([\d.]+)\s*(GiB|MiB|KiB|B)"
)

_MEMORY_BREAKDOWN_RE = re.compile(
    r"common_memory_breakdown_print:.*?\|\s*(\d+)\s*=\s*(\d+)\s*\+\s*"
    r"\((\d+)\s*=\s*(\d+)\s*\+\s*(\d+)\s*\+\s*(\d+)\s*\+\s*(\d+)\).*"
)

_GGUF_KV_RE = re.compile(
    r"^\s*\(?\s*([\w.]+)\s*\)?\s*:\s*(.+)$"
)


def _parse_size_to_bytes(size_str, unit):
    """Convert a size string with unit to bytes."""
    multipliers = {
        "GiB": 1024 ** 3,
        "MiB": 1024 ** 2,
        "KiB": 1024,
        "B": 1,
    }
    return int(float(size_str) * multipliers.get(unit, 1))


def parse_log(log_path):
    """Parse a llama-server log file and extract architecture metadata.

    Returns a dict with keys: architecture, n_layers, n_embd, n_head, n_head_kv,
    n_ctx_train, key_length, value_length, file_size_bytes, model_path.
    Returns None if the log file doesn't exist or can't be parsed.
    """
    if not os.path.exists(log_path):
        return None

    result = {}
    file_size_bytes = None

    with open(log_path, "r") as f:
        for line in f:
            # Parse print_info lines (architecture params)
            m = _PRINT_INFO_RE.match(line.strip())
            if m:
                key, val = m.group(1), m.group(2).strip()
                try:
                    result[key] = int(val)
                except ValueError:
                    result[key] = val
                continue

            # Parse file size line
            m = _FILE_SIZE_RE.match(line.strip())
            if m:
                file_size_bytes = _parse_size_to_bytes(m.group(1), m.group(2))
                continue

    if not result:
        return None

    return {
        "architecture": result.get("architecture", result.get("arch", "unknown")),
        "n_layers": result.get("n_layer"),
        "n_embd": result.get("n_embd"),
        "n_head": result.get("n_head"),
        "n_head_kv": result.get("n_head_kv"),
        "n_ctx_train": result.get("n_ctx_train"),
        "key_length": result.get("key_length"),
        "value_length": result.get("value_length"),
        "file_size_bytes": file_size_bytes,
    }


def parse_memory_breakdown(log_path):
    """Extract VRAM memory breakdown from common_memory_breakdown_print line.

    Format: total = free + (self = model + context + compute) + unaccounted

    Returns a dict with keys: total_mb, free_mb, self_mb, model_mb,
    context_mb, compute_mb, or None if not found.
    """
    if not os.path.exists(log_path):
        return None

    with open(log_path, "r") as f:
        for line in f:
            m = _MEMORY_BREAKDOWN_RE.match(line.strip())
            if m:
                total_mb = int(m.group(1))
                free_mb = int(m.group(2))
                self_mb = int(m.group(3))
                model_mb = int(m.group(4))
                context_mb = int(m.group(5))
                compute_mb = int(m.group(6))
                # group(7) is the last number inside the parens (compute aux)

                # Estimate context per token: use the ctx_size from print_info
                ctx_tokens = _get_ctx_from_log(log_path)
                if not ctx_tokens or context_mb == 0:
                    ctx_per_token_mb = None
                else:
                    ctx_per_token_mb = round(context_mb / ctx_tokens, 6)

                return {
                    "total_mb": total_mb,
                    "free_mb": free_mb,
                    "self_mb": self_mb,
                    "model_mb": model_mb,
                    "context_mb": context_mb,
                    "compute_mb": compute_mb,
                    "ctx_per_token_mb": ctx_per_token_mb,
                    "est_max_ctx_tokens": (
                        int(free_mb / ctx_per_token_mb)
                        if ctx_per_token_mb and ctx_per_token_mb > 0
                        else None
                    ),
                }
    return None


def _get_ctx_from_log(log_path):
    """Extract ctx_size (n_ctx) from a log file's print_info lines."""
    with open(log_path, "r") as f:
        for line in f:
            m = _PRINT_INFO_RE.match(line.strip())
            if m and m.group(1) == "n_ctx":
                try:
                    return int(m.group(2).strip())
                except ValueError:
                    pass
    return None


def get_or_parse_metadata(model_path, log_path=None):
    """Get model metadata from DB, or parse from log if not cached.

    Args:
        model_path: Path to the model file (primary key in model_metadata).
        log_path: Optional path to a llama-server log file for parsing.

    Returns dict of metadata, or None if neither DB nor log is available.
    """
    # Check DB first
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM model_metadata WHERE model_path = %s",
                    (model_path,),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
    except Exception:
        pass

    # Parse from log if available
    if log_path:
        parsed = parse_log(log_path)
        if parsed and parsed.get("n_layers"):
            # Store in DB
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "INSERT INTO model_metadata "
                            "(model_path, architecture, n_layers, n_embd, n_head, "
                            "n_head_kv, n_ctx_train, key_length, value_length, "
                            "file_size_bytes) "
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                            "ON DUPLICATE KEY UPDATE "
                            "architecture=VALUES(architecture), n_layers=VALUES(n_layers), "
                            "n_embd=VALUES(n_embd), n_head=VALUES(n_head), "
                            "n_head_kv=VALUES(n_head_kv), n_ctx_train=VALUES(n_ctx_train), "
                            "key_length=VALUES(key_length), value_length=VALUES(value_length), "
                            "file_size_bytes=VALUES(file_size_bytes)",
                            (
                                model_path,
                                parsed.get("architecture"),
                                parsed.get("n_layers"),
                                parsed.get("n_embd"),
                                parsed.get("n_head"),
                                parsed.get("n_head_kv"),
                                parsed.get("n_ctx_train"),
                                parsed.get("key_length"),
                                parsed.get("value_length"),
                                parsed.get("file_size_bytes"),
                            ),
                        )
                        conn.commit()
            except Exception:
                pass

            # Add model_path to the returned dict
            parsed["model_path"] = model_path
            return parsed

    return None
