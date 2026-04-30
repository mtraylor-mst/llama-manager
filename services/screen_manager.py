import subprocess
import shlex
from config import SCREEN_PREFIX


def _find_active_screen():
    """Find any running screen session matching our prefix pattern."""
    try:
        result = subprocess.run(
            ['screen', '-ls'],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if SCREEN_PREFIX in line and ('Detached' in line or 'Attached' in line):
                parts = line.strip().split()
                if parts:
                    raw_name = parts[0].rstrip('.')
                    # screen -ls returns "pid.name" — strip the PID prefix
                    if '.' in raw_name:
                        screen_name = raw_name.split('.', 1)[1]
                    else:
                        screen_name = raw_name
                    state = 'attached' if 'Attached' in line else 'detached'
                    return screen_name, state
        return None, None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None, None


def get_log_file():
    """Get the log file path for the currently running session."""
    screen_name, _ = _find_active_screen()
    if screen_name:
        return f'/tmp/{screen_name}.log'
    return None


def get_running_version_id():
    """Extract the version_id from the running screen session name.

    Screen names follow pattern: {prefix}-{version_id}
    Returns int version_id or None.
    """
    screen_name, _ = _find_active_screen()
    if not screen_name:
        return None
    # Extract version_id from "llama-manager-{id}"
    prefix_with_dash = f'{SCREEN_PREFIX}-'
    if screen_name.startswith(prefix_with_dash):
        try:
            return int(screen_name[len(prefix_with_dash):])
        except ValueError:
            return None
    return None


def is_running():
    """Check if a screen session with our prefix is running."""
    name, _ = _find_active_screen()
    return name is not None


def get_status():
    """Get detailed status of the screen session."""
    screen_name, state = _find_active_screen()
    if screen_name:
        try:
            result = subprocess.run(
                ['screen', '-ls'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if screen_name in line:
                    return {
                        'running': True,
                        'state': state,
                        'name': screen_name,
                        'line': line.strip(),
                    }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return {'running': True, 'state': state or 'unknown', 'name': screen_name, 'line': ''}
    return {'running': False, 'state': 'stopped', 'name': None, 'line': ''}


def stop():
    """Stop the running screen session."""
    screen_name, _ = _find_active_screen()
    if not screen_name:
        return {'success': True, 'message': 'No session running'}

    try:
        result = subprocess.run(
            ['screen', '-S', screen_name, '-X', 'quit'],
            capture_output=True, text=True, timeout=10
        )
        import time
        time.sleep(1)
        return {'success': not is_running(), 'message': f'Session {screen_name} stopped'}
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Timeout stopping session'}


def start(command, version_id=None):
    """Start llama-server in a screen session. Stops existing session first."""
    if is_running():
        stop()
        import time
        time.sleep(2)

    # Build screen name: prefix-{version_id} for uniqueness across configs
    if version_id:
        screen_name = f'{SCREEN_PREFIX}-{version_id}'
    else:
        screen_name = SCREEN_PREFIX

    # Redirect stdout/stderr to a log file so we can stream it
    log_file = f'/tmp/{screen_name}.log'
    wrapped_command = f'{command} >> {log_file} 2>&1'

    try:
        subprocess.run(
            ['screen', '-dmS', screen_name, 'bash', '-c', wrapped_command],
            check=True, timeout=10
        )
        return {'success': True, 'message': f'Started {screen_name}'}
    except subprocess.CalledProcessError as e:
        return {'success': False, 'message': f'Failed to start: {e.stderr or str(e)}'}
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Timeout starting session'}


def get_logs(lines=50):
    """Get recent logs from llama-server via screen hardcopy."""
    screen_name, _ = _find_active_screen()
    if not screen_name:
        return ''

    try:
        result = subprocess.run(
            ['screen', '-S', screen_name, '-X', 'hardcopy', '/tmp/llama-screen.log'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            with open('/tmp/llama-screen.log', 'r') as f:
                return f.read()
        return ''
    except (subprocess.TimeoutExpired, FileNotFoundError, IOError):
        return ''
