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
    )

    config = get_config(config_id)
    if not config:
        flash("Config not found", "error")
        return redirect(url_for("index"))

    latest = get_latest_version(config_id)
    versions = get_all_versions(config_id)

    # Check if any version of this config is currently running
    from services.screen_manager import get_running_for_config

    running_vid, running_version, running_is_this_config = get_running_for_config(
        config_id, versions
    )

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


@bp.route("/templates")
def templates():
    """List all available templates."""
    from models.templates import get_all_templates, get_template_variables

    templates_list = []
    for t in get_all_templates():
        t["variables"] = get_template_variables(t["id"])
        templates_list.append(t)

    return render_template("templates/index.html", templates=templates_list)


@bp.route("/version/<int:version_id>/template/new", methods=["GET", "POST"])
def new_template(version_id):
    """Create a template from an existing version."""
    from models.configs import get_version
    from models.templates import create_template, save_template_variables

    version = get_version(version_id)
    if not version:
        flash("Version not found", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        if not name:
            flash("Template name is required", "error")
        else:
            template_id = create_template(name, description, version_id)

            # Process variables from form
            variables = []
            i = 0
            while True:
                var_name = request.form.get(f"var_{i}_name", "").strip()
                if not var_name:
                    break
                variables.append({
                    "variable_name": var_name,
                    "display_label": request.form.get(f"var_{i}_label", "").strip(),
                    "default_value": request.form.get(f"var_{i}_default", "").strip(),
                    "hint": request.form.get(f"var_{i}_hint", "").strip(),
                })
                i += 1

            save_template_variables(template_id, variables)
            flash(f"Template '{name}' created", "success")
            return redirect(url_for("configs.templates"))

    # GET — pre-populate suggested variables
    from models.configs import get_all_version_data

    data = get_all_version_data(version_id)
    suggested_vars = _get_suggested_variables(data)

    return render_template(
        "templates/new.html",
        version=version,
        suggested_vars=suggested_vars,
    )


@bp.route("/template/<int:template_id>/instantiate", methods=["GET", "POST"])
def instantiate(template_id):
    """Instantiate a new config from a template."""
    from models.templates import get_template, get_template_variables, instantiate_template

    template = get_template(template_id)
    if not template:
        flash("Template not found", "error")
        return redirect(url_for("configs.templates"))

    variables = get_template_variables(template_id)

    if request.method == "POST":
        config_name = request.form.get("config_name", "").strip()
        if not config_name:
            flash("Config name is required", "error")
        else:
            var_values = {}
            for v in variables:
                key = f"var_{v['variable_name']}"
                val = request.form.get(key, v.get("default_value", "") or "").strip()
                var_values[v["variable_name"]] = val

            config_id, version_id = instantiate_template(
                template_id, config_name, var_values
            )
            if config_id:
                flash(f"Config '{config_name}' created from template", "success")
                return redirect(url_for("versions.edit", version_id=version_id))
            else:
                flash("Failed to create config from template", "error")

    return render_template(
        "templates/instantiate.html",
        template=template,
        variables=variables,
    )


@bp.route("/template/<int:template_id>/delete", methods=["POST"])
def delete_template(template_id):
    """Delete a template."""
    from models.templates import delete_template

    if delete_template(template_id):
        flash("Template deleted", "success")
    else:
        flash("Template not found", "error")
    return redirect(url_for("configs.templates"))


def _get_suggested_variables(data):
    """Suggest fields that are good candidates for templating variables.

    Returns list of dicts with 'variable_name', 'display_label', 'default_value'.
    """
    suggestions = []

    # Model path is the most common variable
    model_path = data.get("model_loading", {}).get("model_path", "")
    if model_path:
        suggestions.append({
            "variable_name": "model_path",
            "display_label": "Model Path",
            "default_value": model_path,
            "hint": "Path to the .gguf model file",
        })

    # Context size is commonly varied per model
    ctx_size = data.get("context_batching", {}).get("ctx_size")
    if ctx_size:
        suggestions.append({
            "variable_name": "ctx_size",
            "display_label": "Context Size",
            "default_value": str(ctx_size),
            "hint": "Context window size in tokens",
        })

    # GPU layers
    gpu_layers = data.get("gpu_device", {}).get("gpu_layers")
    if gpu_layers:
        suggestions.append({
            "variable_name": "gpu_layers",
            "display_label": "GPU Layers",
            "default_value": str(gpu_layers),
            "hint": "Number of layers to offload to GPU (-1 = all)",
        })

    return suggestions
