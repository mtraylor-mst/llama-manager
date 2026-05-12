from flask import Blueprint, render_template, redirect, url_for, request, flash

bp = Blueprint("configs", __name__)


@bp.route("/config/new", methods=["GET", "POST"])
def new():
    from models.configs import create_config

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        model_dir = request.form.get("model_dir", "").strip()
        if not name:
            flash("Name is required", "error")
            return render_template("configs/form.html", config=None)
        cfg_id = create_config(name, description, model_dir)
        # Create initial version
        from models.configs import create_version

        create_version(cfg_id)
        return redirect(url_for("versions.edit_latest", config_id=cfg_id))

    return render_template("configs/form.html", config=None)


@bp.route("/config/<int:config_id>")
def view(config_id):
    from models.configs import (
        get_config,
        get_latest_version,
        get_all_versions,
        get_performance_metrics,
        get_version,
    )

    config = get_config(config_id)
    if not config:
        flash("Config not found", "error")
        return redirect(url_for("index"))

    latest = get_latest_version(config_id)
    versions = get_all_versions(config_id)

    # Check if any version of this config is currently running
    from services.screen_manager import get_running_version_id

    running_vid = get_running_version_id()
    running_is_this_config = False
    running_version = None
    if running_vid:
        for v in versions:
            vid = v["id"] if isinstance(v, dict) else v[0]
            if vid == running_vid:
                running_is_this_config = True
                running_version = get_version(running_vid)
                break

    # Show the running version in the main card if it's from this config, otherwise latest
    featured = running_version if running_is_this_config else latest
    metrics = get_performance_metrics(featured["id"]) if featured else []

    return render_template(
        "configs/view.html",
        config=config,
        featured=featured,
        latest=latest,
        versions=versions,
        metrics=metrics,
        running_version_id=running_vid if running_is_this_config else None,
    )


@bp.route("/config/<int:config_id>/benchmarks")
def benchmarks(config_id):
    from models.configs import (
        get_config,
        get_all_versions,
        get_all_config_benchmarks,
    )
    from services.screen_manager import get_running_version_id

    config = get_config(config_id)
    if not config:
        flash("Config not found", "error")
        return redirect(url_for("index"))

    versions = get_all_versions(config_id)
    benchmarks_data = get_all_config_benchmarks(config_id)
    running_vid = get_running_version_id()

    return render_template(
        "configs/benchmarks.html",
        config=config,
        versions=versions,
        benchmarks=benchmarks_data,
        running_version_id=running_vid,
    )


@bp.route("/config/<int:config_id>/benchmark/<int:metric_id>/delete", methods=["POST"])
def delete_benchmark(config_id, metric_id):
    from models.configs import delete_performance_metric

    if not delete_performance_metric(metric_id):
        flash("Benchmark not found", "error")
    else:
        flash("Benchmark deleted", "success")
    return redirect(url_for("configs.benchmarks", config_id=config_id))


@bp.route("/benchmarks/compare")
def compare_benchmarks():
    from models.configs import get_all_configs, get_all_model_benchmarks

    config_ids = request.args.getlist("config_id", type=int)
    all_configs = get_all_configs()

    benchmarks_data = []
    if config_ids:
        benchmarks_data = get_all_model_benchmarks(config_ids)

    return render_template(
        "configs/compare_benchmarks.html",
        configs=all_configs,
        selected_config_ids=config_ids,
        benchmarks=benchmarks_data,
    )


@bp.route("/config/<int:config_id>/edit", methods=["GET", "POST"])
def edit(config_id):
    from models.configs import get_config, update_config

    config = get_config(config_id)
    if not config:
        flash("Config not found", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        model_dir = request.form.get("model_dir", "").strip()
        if not name:
            flash("Name is required", "error")
        else:
            update_config(config_id, name, description, model_dir)
            return redirect(url_for("configs.view", config_id=config_id))

    return render_template("configs/form.html", config=config)


@bp.route("/config/<int:config_id>/delete", methods=["POST"])
def delete(config_id):
    from models.configs import delete_config

    delete_config(config_id)
    flash("Config deleted", "success")
    return redirect(url_for("index"))
