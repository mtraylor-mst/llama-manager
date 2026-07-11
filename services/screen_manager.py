import os
import signal
import subprocess
import time

_PID_FILE = "/tmp/.llama-manager.pid"
_STATUS_CACHE = {"value": None, "timestamp": 0}
_STATUS_TTL = 2


def _invalidate_status_cache():
    """Clear the status cache (call after start/stop)."""
    _STATUS_CACHE["value"] = None
    _STATUS_CACHE["timestamp"] = 0


def _write_pid(pid, version_id=None):
    """Write the server PID and version_id to a file for recovery across restarts."""
    with open(_PID_FILE, "w") as f:
        f.write(f"{pid}\n{version_id or ''}")


def _read_pid():
    """Read and validate the stored PID. Returns (pid, version_id) or (None, None)."""
    if not os.path.exists(_PID_FILE):
        return None, None
    try:
        with open(_PID_FILE, "r") as f:
            lines = f.read().strip().split("\n")
        pid = int(lines[0])
        vid = int(lines[1]) if len(lines) > 1 and lines[1].isdigit() else None
        # Check if process is actually running and owned by us
        if _is_our_process(pid):
            return pid, vid
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        pass
    return None, None


def _cleanup_pid():
    """Remove the PID file."""
    try:
        os.remove(_PID_FILE)
    except OSError:
        pass


def get_log_file(version_id=None):
    """Get the log file path for a version."""
    if version_id:
        return f"/tmp/llama-server-{version_id}.log"
    return "/tmp/llama-server.log"


def _is_our_process(pid):
    """Check if a PID belongs to a llama-server process owned by the current user.

    Verifies:
    1. The process is signalable by us.
    2. The process UID matches our UID.
    3. The command name contains 'llama-server'.

    Returns True only if all checks pass.
    """
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False

    # Verify the process is owned by our user
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            found_uid = False
            for line in f.readlines():
                if line.startswith("Uid:"):
                    proc_uid = int(line.split()[1])
                    if proc_uid != os.getuid():
                        return False
                    found_uid = True
                    break
            if not found_uid:
                return False
    except (FileNotFoundError, PermissionError, ValueError, OSError):
        return False

    # Verify the command name is llama-server
    try:
        with open(f"/proc/{pid}/comm", "r") as f:
            comm = f.read().strip()
            if "llama-server" not in comm:
                return False
    except (FileNotFoundError, PermissionError, OSError):
        return False

    return True


def _extract_version_id_from_log(log_path):
    """Extract version_id from a log file path like /tmp/llama-server-42.log."""
    base = os.path.basename(log_path).replace(".log", "")
    vid_str = None
    for prefix in ["llama-server-", "llama-server"]:
        if base.startswith(prefix):
            vid_str = base[len(prefix) :]
            break
    return int(vid_str) if vid_str and vid_str.isdigit() else None


def _find_running():
    """Find any running llama-server process we own.

    This is a read-only operation — it does not mutate state.

    Returns (pid, version_id) or (None, None).
    """
    # First check our PID file
    pid, vid = _read_pid()
    if pid:
        return pid, vid

    # Fallback 1: scan for llama-server processes with our log files via lsof
    import glob as glob_module

    for log_path in glob_module.glob("/tmp/llama-server-*.log"):
        try:
            result = subprocess.run(
                ["lsof", "-t", log_path], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for p in pids:
                    try:
                        p = int(p)
                        if _is_our_process(p):
                            vid = _extract_version_id_from_log(log_path)
                            return p, vid
                    except (ValueError, ProcessLookupError):
                        continue
        except Exception:
            continue

    # Fallback 2: find llama-server by process name via pgrep
    try:
        result = subprocess.run(
            ["pgrep", "-x", "llama-server"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            for p in result.stdout.strip().split("\n"):
                try:
                    p = int(p)
                    if not _is_our_process(p):
                        continue
                    # Determine version_id from stdout log file via /proc/pid/fd/1
                    fd_target = os.readlink(f"/proc/{p}/fd/1")
                    if fd_target.startswith("/tmp/llama-server-"):
                        vid = _extract_version_id_from_log(fd_target)
                        return p, vid
                    # Process found but stdout not a managed log file — return with vid=None
                    return p, None
                except (ValueError, ProcessLookupError, OSError):
                    continue
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None, None


def _find_running_cached():
    """Find running server with TTL cache to avoid expensive I/O on every request."""
    now = time.time()
    if now - _STATUS_CACHE["timestamp"] < _STATUS_TTL:
        return _STATUS_CACHE["value"]
    result = _find_running()
    _STATUS_CACHE["value"] = result
    _STATUS_CACHE["timestamp"] = now
    return result


def get_running_version_id():
    """Get the version_id of the currently running server."""
    _, vid = _find_running_cached()
    return vid


def is_running():
    """Check if a llama-server process we own is running."""
    return _find_running()[0] is not None


def get_status():
    """Get detailed status of the running server."""
    pid, vid = _find_running_cached()
    if pid:
        return {
            "running": True,
            "state": "running",
            "name": f"PID {pid}",
            "line": "",
        }
    return {"running": False, "state": "stopped", "name": None, "line": ""}


def get_running_for_config(config_id, versions=None):
    """Check if a version of config_id is currently running.

    Args:
        config_id: The config to check against.
        versions: Optional pre-fetched list of version dicts for this config.
                  If provided, returns the matching dict from that list.

    Returns:
        Tuple of (running_vid, running_version, is_this_config).
        running_version is None if not from this config.
    """
    running_vid = get_running_version_id()
    if not running_vid:
        return None, None, False

    if versions:
        for v in versions:
            if v["id"] == running_vid:
                return running_vid, v, True
        return running_vid, None, False

    # No pre-fetched list — check by loading the running version
    from models.configs import get_version

    ver = get_version(running_vid)
    is_this = ver and ver["config_id"] == config_id
    return running_vid, ver if is_this else None, is_this


def stop():
    """Stop the running llama-server process."""
    pid, _ = _find_running()
    if not pid:
        return {"success": True, "message": "No server running"}

    try:
        os.kill(pid, signal.SIGTERM)
        import time

        # Wait up to 5 seconds for graceful shutdown
        for _ in range(50):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                _cleanup_pid()
                _invalidate_status_cache()
                return {"success": True, "message": f"Server (PID {pid}) stopped"}
        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        _cleanup_pid()
        _invalidate_status_cache()
        return {"success": True, "message": f"Server (PID {pid}) killed"}
    except ProcessLookupError:
        _cleanup_pid()
        _invalidate_status_cache()
        return {"success": True, "message": "Server already stopped"}
    except Exception as e:
        return {"success": False, "message": f"Failed to stop: {e}"}


def start(args, version_id=None):
    """Start llama-server directly via subprocess. Stops existing process first.

    args: list of command arguments (no shell interpretation).
    """
    if is_running():
        stop()
        import time

        time.sleep(2)

    log_file = get_log_file(version_id)

    try:
        with open(log_file, "a") as log_fd:
            proc = subprocess.Popen(
                args,
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        _write_pid(proc.pid, version_id)
        _invalidate_status_cache()
        return {"success": True, "message": f"Started (PID {proc.pid})"}
    except Exception as e:
        return {"success": False, "message": f"Failed to start: {e}"}


def get_logs(lines=50):
    """Get recent lines from the server log file."""
    pid, vid = _find_running()
    if not pid:
        return ""

    log_file = get_log_file(vid)
    try:
        result = subprocess.run(
            ["tail", "-n", str(lines), log_file],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""
