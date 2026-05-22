"""Stress test orchestrator for VRAM compaction and OOM prediction."""

import json
import logging
import os
import threading
import time
import urllib.request
import zipfile

from models.base import get_conn
from services.model_parser import get_or_parse_metadata, parse_memory_breakdown
from services.vram_monitor import VramMonitor

logger = logging.getLogger(__name__)

# Global state for stress test management
_active_tests = {}  # test_id -> thread
_active_lock = threading.Lock()

WIKITEXT_URL = "https://s3.amazonaws.com/research.metamind.io/wikitext/wikitext-2-raw-v1.zip"
WIKITEXT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wikitext.txt")


def _ensure_wikitext():
    """Download wikitext-2 raw if not already present. Returns path to text file."""
    if os.path.exists(WIKITEXT_PATH):
        return WIKITEXT_PATH

    os.makedirs(os.path.dirname(WIKITEXT_PATH), exist_ok=True)
    zip_path = WIKITEXT_PATH + ".zip"

    logger.info("Downloading wikitext-2...")
    urllib.request.urlretrieve(WIKITEXT_URL, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".raw"):
                zf.extract(name, os.path.dirname(WIKITEXT_PATH))
                raw_path = os.path.join(os.path.dirname(WIKITEXT_PATH), name)
                os.rename(raw_path, WIKITEXT_PATH)
                break

    os.remove(zip_path)
    return WIKITEXT_PATH


def _get_server_url(version_data):
    """Build base URL for llama-server API from version config."""
    server = version_data.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("port", 8080)
    if not host or not port:
        return f"http://127.0.0.1:{port or 8080}"
    return f"http://{host}:{port}"


def _wait_for_server(base_url, timeout=60):
    """Wait until llama-server /health endpoint responds. Returns True if ready."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(f"{base_url}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _tokenize_prompt(base_url, text):
    """Use llama-server /tokenize endpoint to get token count for text."""
    try:
        data = json.dumps({"content": text}).encode()
        req = urllib.request.Request(
            f"{base_url}/tokenize",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("tokens", [])
    except Exception:
        return None


def _make_prompt_of_length(base_url, target_tokens):
    """Create a prompt that tokenizes to exactly target_tokens using wikitext."""
    wikitext_path = _ensure_wikitext()
    with open(wikitext_path, "r") as f:
        raw_text = f.read()

    # First tokenize a large chunk to get a token pool
    # Use iterative approach: start with estimate, adjust
    # Rough chars-per-token estimate for English: ~4
    estimate_chars = target_tokens * 4
    candidate = raw_text[:estimate_chars]

    tokens = _tokenize_prompt(base_url, candidate)
    if not tokens:
        return None

    # Iterative refinement for exact token count
    best_text = candidate
    best_diff = abs(len(tokens) - target_tokens)

    for _ in range(20):
        current_tokens = _tokenize_prompt(base_url, candidate)
        if not current_tokens:
            break
        current_len = len(current_tokens)
        diff = current_len - target_tokens

        if abs(diff) < best_diff:
            best_text = candidate
            best_diff = abs(diff)

        if diff == 0:
            break
        elif diff > 0:
            # Too many tokens, reduce
            reduction = int(abs(diff) * 4)
            candidate = candidate[:-reduction] if reduction > 0 else candidate[:len(candidate) - 1]
        else:
            # Too few tokens, increase
            addition = int(abs(diff) * 4)
            new_len = min(len(candidate) + addition, len(raw_text))
            candidate = raw_text[:new_len]

    return best_text


def _send_completion(base_url, prompt, n_predict=1):
    """Send a completion request. Returns timing info dict or None on failure."""
    try:
        data = json.dumps({
            "prompt": prompt,
            "n_predict": n_predict,
            "cache_prompt": True,
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/completion",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        start = time.time()
        with urllib.request.urlopen(req, timeout=300) as resp:
            elapsed = time.time() - start
            result = json.loads(resp.read().decode())
            return {
                "success": True,
                "elapsed": elapsed,
                "tokens_predicted": result.get("tokens_predicted", 0),
                "tokens_cached": result.get("tokens_cached", 0),
                "tps": result.get("timings", {}).get("predicted_per_s", 0),
            }
    except Exception as e:
        logger.warning(f"Completion request failed: {e}")
        return {"success": False, "elapsed": 0, "tps": 0}


def _build_command_with_ctx(version_id, ctx_size):
    """Build command args for version_id but override ctx_size."""
    from services.command_builder import build_command

    args = build_command(version_id)
    # Replace --ctx-size value if present, or append it
    new_args = []
    i = 0
    found = False
    while i < len(args):
        if args[i] in ("-c", "--ctx-size"):
            new_args.append("-c")
            new_args.append(str(ctx_size))
            i += 2
            found = True
        else:
            new_args.append(args[i])
            i += 1
    if not found:
        new_args.extend(["-c", str(ctx_size)])
    return new_args


def _run_single_step(base_url, ctx_tokens, monitor):
    """Run a single stress test step. Returns data point dict or None on failure."""
    monitor.start()

    # Wait for VRAM to stabilize after server start
    time.sleep(2)
    baseline_readings = []
    for _ in range(5):
        peak = monitor.get_peak()
        if peak is not None:
            baseline_readings.append(peak)
        time.sleep(0.2)
    baseline_vram = min(baseline_readings) if baseline_readings else None

    # Get prompt of exact token length
    prompt = _make_prompt_of_length(base_url, ctx_tokens)
    if not prompt:
        monitor.stop()
        return None

    # Send completion to fill KV cache
    result = _send_completion(base_url, prompt, n_predict=1)
    if not result or not result["success"]:
        monitor.stop()
        return None

    # Give VRAM time to settle after generation
    time.sleep(2)
    peak_vram = monitor.get_peak()
    data_points = monitor.stop()

    # Get final steady reading (last few samples)
    steady_vram = None
    if data_points:
        steady_vram = data_points[-1][1]

    tps = result.get("tps", 0)

    return {
        "ctx_tokens": ctx_tokens,
        "vram_used_mb": steady_vram,
        "peak_vram_mb": peak_vram,
        "tps": round(tps, 2) if tps else None,
        "baseline_vram_mb": baseline_vram,
    }


def _derive_metrics(data_points_list):
    """Derive compaction_coefficient and kv_per_token_bytes from data points."""
    if not data_points_list:
        return None, None

    # Compaction coefficient: max(peak_vram / steady_vram - 1) across steps
    compaction_coeff = None
    for dp in data_points_list:
        peak = dp.get("peak_vram_mb")
        steady = dp.get("vram_used_mb")
        if peak and steady and steady > 0:
            coeff = peak / steady - 1
            if compaction_coeff is None or coeff > compaction_coeff:
                compaction_coeff = coeff

    # Linear regression: vram_used_mb vs ctx_tokens for kv_per_token_bytes
    n = len(data_points_list)
    if n < 2:
        return round(compaction_coeff, 4) if compaction_coeff is not None else None, None

    xs = [dp["ctx_tokens"] for dp in data_points_list]
    ys = [(dp.get("vram_used_mb") or 0) * 1024 * 1024 for dp in data_points_list]

    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return round(compaction_coeff, 4) if compaction_coeff is not None else None, None

    slope = (n * sum_xy - sum_x * sum_y) / denom
    kv_per_token_bytes = round(slope, 4)

    return round(compaction_coeff, 4) if compaction_coeff is not None else None, kv_per_token_bytes


def run_stress_test(version_id):
    """Start a stress test in a background thread.

    Returns dict with test_id on success, or error info on failure.
    Only one stress test can run at a time.
    """
    # Check for concurrent test
    with _active_lock:
        if _active_tests:
            existing_id = next(iter(_active_tests))
            return {
                "error": "A stress test is already running",
                "running_test_id": existing_id,
            }

    # Create DB record
    total_vram = VramMonitor.get_total_vram()
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO vram_stress_tests (version_id, total_vram_mb, status) "
                    "VALUES (%s, %s, 'running')",
                    (version_id, total_vram),
                )
                conn.commit()
                test_id = cur.lastrowid
    except Exception as e:
        return {"error": f"Failed to create test record: {e}"}

    # Spawn thread
    thread = threading.Thread(
        target=_execute_stress_test,
        args=(test_id, version_id),
        daemon=True,
    )
    with _active_lock:
        _active_tests[test_id] = thread
    thread.start()

    return {"test_id": test_id}


def _execute_stress_test(test_id, version_id):
    """Execute the stress test steps. Updates DB as it progresses."""
    from services.screen_manager import stop, start, get_log_file
    from models.configs import get_version, get_category, get_all_version_data

    try:
        # Get version data
        version_info = get_version(version_id)
        if not version_info:
            _finish_test(test_id, status="failed", error_msg="Version not found")
            return

        all_data = get_all_version_data(version_id)
        model_loading = all_data.get("model_loading", {})
        model_path = model_loading.get("model_path", "")
        base_ctx = get_category(version_id, "context_batching").get("ctx_size", 2048)

        # Parse model metadata from existing log or quick probe
        log_path = get_log_file(version_id)
        if not os.path.exists(log_path):
            # Quick startup to generate log
            logger.info(f"Starting server for log generation (test {test_id})")
            args = _build_command_with_ctx(version_id, base_ctx)
            start_result = start(args, version_id=version_id)
            if not start_result.get("success"):
                _finish_test(test_id, status="failed", error_msg=start_result.get("message", "Failed to start"))
                return

            server_data = all_data.get("server", {})
            base_url = _get_server_url({"server": server_data})
            if not _wait_for_server(base_url, timeout=120):
                stop()
                _finish_test(test_id, status="failed", error_msg="Server failed to start")
                return

            # Wait for log to be written
            time.sleep(3)
            stop()
            time.sleep(2)

        metadata = get_or_parse_metadata(model_path, log_path)
        if not metadata:
            _finish_test(test_id, status="failed", error_msg="Failed to parse model metadata")
            return

        # Parse memory breakdown for estimates
        breakdown = parse_memory_breakdown(log_path)
        if breakdown and breakdown.get("est_max_ctx_tokens"):
            est_failure = breakdown["est_max_ctx_tokens"]
        elif metadata.get("n_ctx_train"):
            est_failure = metadata["n_ctx_train"]
        else:
            est_failure = 32768  # Conservative default

        model_weight_size_mb = (
            int(metadata["file_size_bytes"] / (1024 * 1024))
            if metadata.get("file_size_bytes")
            else None
        )

        # Update test record with model weight size
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE vram_stress_tests SET model_weight_size_mb = %s WHERE id = %s",
                    (model_weight_size_mb, test_id),
                )

        # Phase A: Aggressive doubling steps up to 80% of estimated failure
        phase_a_steps = []
        step = 1024
        while step <= int(est_failure * 0.8):
            phase_a_steps.append(step)
            step *= 2

        # Cap at n_ctx_train if available
        max_ctx = metadata.get("n_ctx_train") or est_failure
        phase_a_steps = [s for s in phase_a_steps if s <= max_ctx]
        if not phase_a_steps:
            phase_a_steps = [1024]

        # Phase B steps will be determined after Phase A
        all_data_points = []
        last_success_ctx = 0
        failure_ctx = None

        # Run server for testing
        server_data = all_data.get("server", {})
        base_url = _get_server_url({"server": server_data})

        # Start server with max ctx we'll need
        max_test_ctx = max(phase_a_steps)
        args = _build_command_with_ctx(version_id, max_test_ctx)
        start_result = start(args, version_id=version_id)
        if not start_result.get("success"):
            _finish_test(test_id, status="failed", error_msg=start_result.get("message", "Failed to start"))
            return

        if not _wait_for_server(base_url, timeout=120):
            stop()
            _finish_test(test_id, status="failed", error_msg="Server failed to start")
            return

        # Phase A
        for ctx_tokens in phase_a_steps:
            logger.info(f"Test {test_id}: Phase A step ctx={ctx_tokens}")
            dp = _run_single_step(base_url, ctx_tokens, VramMonitor())
            if dp:
                all_data_points.append(dp)
                last_success_ctx = ctx_tokens
                _store_data_point(test_id, dp)
            else:
                failure_ctx = ctx_tokens
                logger.warning(f"Test {test_id}: Phase A failed at ctx={ctx_tokens}")
                break

        # Phase B: Fine granularity from last success toward estimated failure
        if last_success_ctx and not failure_ctx:
            phase_b_start = last_success_ctx
            phase_b_end = min(int(est_failure * 0.95), max_ctx)
            increment = 512

            ctx = phase_b_start + increment
            while ctx <= phase_b_end:
                logger.info(f"Test {test_id}: Phase B step ctx={ctx}")
                dp = _run_single_step(base_url, ctx, VramMonitor())
                if dp:
                    all_data_points.append(dp)
                    last_success_ctx = ctx
                    _store_data_point(test_id, dp)
                else:
                    failure_ctx = ctx
                    logger.warning(f"Test {test_id}: Phase B failed at ctx={ctx}")
                    break
                ctx += increment

        # Derive metrics
        compaction_coeff, kv_per_token = _derive_metrics(all_data_points)

        # If no failure detected, set failure_ctx to None (didn't reach OOM in test range)
        if failure_ctx is None and all_data_points:
            failure_ctx = None  # Successfully tested entire range

        # Finish test
        _finish_test(
            test_id,
            status="completed" if not failure_ctx or all_data_points else "failed",
            compaction_coeff=compaction_coeff,
            kv_per_token_bytes=kv_per_token,
            failure_ctx_tokens=failure_ctx,
        )

    except Exception as e:
        logger.error(f"Test {test_id}: Unexpected error: {e}", exc_info=True)
        _finish_test(test_id, status="failed", error_msg=str(e))
    finally:
        with _active_lock:
            _active_tests.pop(test_id, None)


def _store_data_point(test_id, dp):
    """Store a single data point in the database."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO vram_stress_data_points "
                    "(stress_test_id, ctx_tokens, vram_used_mb, peak_vram_mb, tps) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        test_id,
                        dp["ctx_tokens"],
                        dp.get("vram_used_mb"),
                        dp.get("peak_vram_mb"),
                        dp.get("tps"),
                    ),
                )
    except Exception as e:
        logger.error(f"Failed to store data point for test {test_id}: {e}")


def _finish_test(test_id, status=None, compaction_coeff=None, kv_per_token_bytes=None,
                 failure_ctx_tokens=None, error_msg=None):
    """Update test record with final status and derived metrics."""
    try:
        updates = []
        params = []

        if status:
            updates.append("status = %s")
            params.append(status)
        if compaction_coeff is not None:
            updates.append("compaction_coefficient = %s")
            params.append(compaction_coeff)
        if kv_per_token_bytes is not None:
            updates.append("kv_per_token_bytes = %s")
            params.append(kv_per_token_bytes)
        if failure_ctx_tokens is not None:
            updates.append("failure_ctx_tokens = %s")
            params.append(failure_ctx_tokens)
        if status in ("completed", "failed"):
            updates.append("completed_at = CURRENT_TIMESTAMP")

        if updates:
            params.append(test_id)
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"UPDATE vram_stress_tests SET {', '.join(updates)} WHERE id = %s",
                        params,
                    )
    except Exception as e:
        logger.error(f"Failed to finish test {test_id}: {e}")


def get_stress_test_status(test_id):
    """Get current status and progress of a stress test."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM vram_stress_tests WHERE id = %s", (test_id,)
                )
                test = cur.fetchone()
                if not test:
                    return None

                cur.execute(
                    "SELECT * FROM vram_stress_data_points "
                    "WHERE stress_test_id = %s ORDER BY ctx_tokens",
                    (test_id,),
                )
                data_points = cur.fetchall()

                is_running = False
                with _active_lock:
                    if test_id in _active_tests:
                        is_running = _active_tests[test_id].is_alive()

                return {
                    "id": test["id"],
                    "version_id": test["version_id"],
                    "status": test["status"],
                    "started_at": str(test["started_at"]) if test["started_at"] else None,
                    "completed_at": str(test["completed_at"]) if test["completed_at"] else None,
                    "total_vram_mb": test["total_vram_mb"],
                    "model_weight_size_mb": test["model_weight_size_mb"],
                    "compaction_coefficient": float(test["compaction_coefficient"]) if test["compaction_coefficient"] else None,
                    "kv_per_token_bytes": float(test["kv_per_token_bytes"]) if test["kv_per_token_bytes"] else None,
                    "failure_ctx_tokens": test["failure_ctx_tokens"],
                    "data_points": [dict(dp) for dp in data_points],
                    "total_steps": len(data_points),
                    "is_running": is_running,
                }
    except Exception as e:
        logger.error(f"Failed to get stress test status for {test_id}: {e}")
        return None


def get_latest_stress_test(version_id):
    """Get the most recent stress test for a version."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM vram_stress_tests "
                    "WHERE version_id = %s ORDER BY started_at DESC LIMIT 1",
                    (version_id,),
                )
                test = cur.fetchone()
                if not test:
                    return None
                return get_stress_test_status(test["id"])
    except Exception as e:
        logger.error(f"Failed to get latest stress test for version {version_id}: {e}")
        return None


def cancel_stress_test(test_id):
    """Cancel a running stress test."""
    with _active_lock:
        thread = _active_tests.get(test_id)
    if thread and thread.is_alive():
        # Stop the server to interrupt the test
        from services.screen_manager import stop
        stop()
        _finish_test(test_id, status="cancelled")
        return True
    return False
