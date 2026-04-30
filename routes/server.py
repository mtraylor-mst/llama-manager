from flask import Blueprint, request, jsonify, flash, redirect, url_for, Response, stream_with_context
import time
import html as html_module

bp = Blueprint('server', __name__)


@bp.route('/server/status')
def status():
    from services.screen_manager import get_status
    st = get_status()
    if request.headers.get('HX-Request'):
        # Return HTML for HTMX swap
        if st['running']:
            return (f'<span class="status running" hx-get="{url_for("server.status")}" '
                    f'hx-trigger="every 10s" hx-swap="outerHTML">'
                    f'● Running '
                    f'<button hx-post="{url_for("server.import_config")}" hx-target="#flash-area" '
                    f'class="btn btn-sm btn-import">Import Config</button> '
                    f'<button hx-post="{url_for("server.stop")}" hx-target="#flash-area" '
                    f'class="btn btn-sm btn-danger">Stop</button></span>')
        else:
            return '<span class="status stopped">● Stopped</span>'
    return jsonify(st)


@bp.route('/server/stop', methods=['POST'])
def stop():
    from services.screen_manager import stop
    result = stop()
    if request.headers.get('HX-Request'):
        cls = 'success' if result['success'] else 'error'
        return f'<div class="alert alert-{cls}">{result["message"] if not result["success"] else "Server stopped"}</div>'
    if result['success']:
        flash('Server stopped', 'success')
    else:
        flash(result['message'], 'error')
    return redirect(request.referrer or url_for('index'))


@bp.route('/server/start/<int:version_id>', methods=['POST'])
def start(version_id):
    from services.screen_manager import start
    from services.command_builder import build_command
    cmd = build_command(version_id)
    result = start(cmd, version_id=version_id)
    if request.headers.get('HX-Request'):
        cls = 'success' if result['success'] else 'error'
        msg = f"Server started (v{version_id})" if result['success'] else result['message']
        return f'<div class="alert alert-{cls}">{msg}</div>'
    if result['success']:
        flash(f'Server started (v{version_id})', 'success')
    else:
        flash(result['message'], 'error')
    return redirect(request.referrer or url_for('index'))


@bp.route('/server/logs')
def logs():
    from services.screen_manager import get_logs
    lines = request.args.get('lines', 50, type=int)
    return jsonify({'logs': get_logs(lines)})


@bp.route('/server/stream-logs')
def stream_logs():
    """SSE endpoint that streams stdout from the running llama-server process."""
    def generate():
        import subprocess
        while True:
            try:
                from services.screen_manager import get_log_file, is_running
                log_file = get_log_file()
                if not log_file or not is_running():
                    yield f'data: [no process running]\n\n'
                    time.sleep(3)
                    continue

                proc = subprocess.Popen(
                    ['tail', '-fn10', log_file],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
                )
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    safe = html_module.escape(line.rstrip('\n'))
                    yield f'data: {safe}\n\n'
            except (subprocess.CalledProcessError, FileNotFoundError, PermissionError,
                    subprocess.TimeoutExpired, IOError):
                pass

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@bp.route('/version/<int:version_id>/benchmark', methods=['POST'])
def benchmark(version_id):
    from services.benchmarks import benchmark_version
    result = benchmark_version(version_id)
    return jsonify(result)


@bp.route('/server/import-config', methods=['POST'])
def import_config():
    from services.config_importer import import_running_config
    config_name = request.form.get('config_name', 'Imported Config')
    try:
        cfg_id, ver_id, parsed, created_new = import_running_config(config_name)
        if request.headers.get('HX-Request'):
            if not created_new:
                return (f'<div class="alert alert-warning">'
                        f'⚠ Settings unchanged — running server matches '
                        f'<a href="{url_for("versions.edit", version_id=ver_id)}">latest version</a> of config.</div>')
            return (f'<div class="alert alert-success">'
                    f'✓ Imported <strong>{len(parsed)}</strong> flags from running server. '
                    f'<a href="{url_for("configs.view", config_id=cfg_id)}">View & edit config →</a></div>')
        if not created_new:
            flash(f'Settings unchanged (matches latest version)', 'warning')
            return redirect(url_for('configs.view', config_id=cfg_id))
        flash(f'Config imported ({len(parsed)} flags)', 'success')
        return redirect(url_for('configs.view', config_id=cfg_id))
    except Exception as e:
        if request.headers.get('HX-Request'):
            return f'<div class="alert alert-error">Import failed: {e}</div>'
        flash(str(e), 'error')
        return redirect(request.referrer or url_for('index'))
