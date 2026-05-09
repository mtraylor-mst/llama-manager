import logging
from flask import (
    Blueprint,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    Response,
    stream_with_context,
)
import html as html_module
from utils.rate_limit import rate_limit

bp = Blueprint("server", __name__)
logger = logging.getLogger(__name__)


@bp.route("/server/status")
def status():
    from services.screen_manager import get_status, get_running_version_id

    st = get_status()
    running_vid = get_running_version_id() if st["running"] else None

    # Look up version details for display
    running_ver_info = None
    if running_vid:
        from models.configs import get_version

        running_ver_info = get_version(running_vid)

    if request.headers.get("HX-Request"):
        # Return HTML for HTMX swap
        if st["running"]:
            ver_label = ""
            if running_ver_info:
                safe_name = html_module.escape(running_ver_info["config_name"])
                ver_label = f' <a href="{url_for("versions.edit", version_id=running_ver_info["id"])}">v{running_ver_info["version_number"]} ({safe_name})</a>'
            return (
                f'<span class="status running" hx-get="{url_for("server.status")}" '
                f'hx-trigger="every 10s" hx-swap="outerHTML">'
                f"● Running{ver_label} "
                f'<button hx-post="{url_for("server.import_config")}" hx-target="#flash-area" '
                f'class="btn btn-import">Import Config</button> '
                f'<button hx-post="{url_for("server.stop")}" hx-target="#flash-area" '
                f'class="btn btn-danger">Stop</button></span>'
            )
        else:
            return '<span class="status stopped">● Stopped</span>'
    return jsonify(st)


@bp.route("/server/stop", methods=["POST"])
@rate_limit(max_calls=3, period=60)
def stop():
    from services.screen_manager import stop

    result = stop()
    if request.headers.get("HX-Request"):
        cls = "success" if result["success"] else "error"
        msg = (
            html_module.escape(result["message"])
            if not result["success"]
            else "Server stopped"
        )
        return f'<div class="alert alert-{cls}">{msg}</div>'
    if result["success"]:
        flash("Server stopped", "success")
    else:
        flash(result["message"], "error")
    return redirect(request.referrer or url_for("index"))


@bp.route("/server/start/<int:version_id>", methods=["POST"])
@rate_limit(max_calls=1, period=30)
def start(version_id):
    from services.screen_manager import start
    from services.command_builder import build_command

    args = build_command(version_id)
    result = start(args, version_id=version_id)
    if request.headers.get("HX-Request"):
        cls = "success" if result["success"] else "error"
        msg = (
            f"Server started (v{version_id})"
            if result["success"]
            else html_module.escape(result["message"])
        )
        return f'<div class="alert alert-{cls}">{msg}</div>'
    if result["success"]:
        flash(f"Server started (v{version_id})", "success")
    else:
        flash(result["message"], "error")
    return redirect(request.referrer or url_for("index"))


@bp.route("/server/logs")
def logs():
    from services.screen_manager import get_logs

    lines = request.args.get("lines", 50, type=int)
    return jsonify({"logs": get_logs(lines)})


@bp.route("/server/stream-logs")
def stream_logs():
    """SSE endpoint that streams stdout from the running llama-server process."""

    def generate():
        import subprocess

        from services.screen_manager import (
            get_log_file,
            get_running_version_id,
            is_running,
        )

        if not is_running():
            yield "data: [no process running]\n\n"
            return

        vid = get_running_version_id()
        log_file = get_log_file(vid)

        proc = None
        try:
            proc = subprocess.Popen(
                ["tail", "-Fn0", log_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            try:
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    safe = html_module.escape(line.rstrip("\n"))
                    yield f"data: {safe}\n\n"
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            PermissionError,
            subprocess.TimeoutExpired,
            IOError,
        ):
            yield "data: [error reading logs]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.route("/version/<int:version_id>/benchmark", methods=["POST"])
@rate_limit(max_calls=1, period=120)
def benchmark(version_id):
    from services.benchmarks import benchmark_version

    result = benchmark_version(version_id)
    return jsonify(result)


@bp.route("/server/import-config", methods=["POST"])
def import_config():
    from services.config_importer import import_running_config

    config_name = request.form.get("config_name", "Imported Config")
    try:
        cfg_id, ver_id, parsed, created_new = import_running_config(config_name)
        if request.headers.get("HX-Request"):
            if not created_new:
                return (
                    f'<div class="alert alert-warning">'
                    f"⚠ Settings unchanged — running server matches "
                    f'<a href="{url_for("versions.edit", version_id=ver_id)}">latest version</a> of config.</div>'
                )
            return (
                f'<div class="alert alert-success">'
                f"✓ Imported <strong>{len(parsed)}</strong> flags from running server. "
                f'<a href="{url_for("configs.view", config_id=cfg_id)}">View & edit config →</a></div>'
            )
        if not created_new:
            flash("Settings unchanged (matches latest version)", "warning")
            return redirect(url_for("configs.view", config_id=cfg_id))
        flash(f"Config imported ({len(parsed)} flags)", "success")
        return redirect(url_for("configs.view", config_id=cfg_id))
    except Exception:
        logger.error("Error importing config", exc_info=True)
        if request.headers.get("HX-Request"):
            return '<div class="alert alert-error">Import failed — check server logs for details.</div>'
        flash("Import failed — check server logs for details.", "error")
        return redirect(request.referrer or url_for("index"))
