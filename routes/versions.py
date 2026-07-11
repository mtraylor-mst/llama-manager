from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    jsonify,
    session,
)
from models.configs import duplicate_version, get_all_version_data
from template_utils import CATEGORY_LABELS

bp = Blueprint("versions", __name__)


def get_common_option_set():
    """Return a set of (category, column_name) tuples for all common options."""
    try:
        from models.configs import get_common_options

        options = get_common_options()
        return {(opt["category"], opt["column_name"]) for opt in options}
    except Exception:
        return set()


def _resolve_option_label(opt):
    """Resolve the display label for a common option."""
    from template_utils import CATEGORY_FIELDS

    fields = CATEGORY_FIELDS.get(opt["category"], [])
    field_def = next((f for f in fields if f[0] == opt["column_name"]), None)
    return opt["custom_label"] or (
        field_def[1] if field_def else opt["column_name"]
    )


def _option_to_dict(opt):
    """Convert a raw common option row to a template-ready dict."""
    return {
        "id": opt["id"],
        "category": opt["category"],
        "column_name": opt["column_name"],
        "label": _resolve_option_label(opt),
    }


def get_common_options_list():
    """Return list of common option dicts with resolved labels."""
    try:
        from models.configs import get_common_options

        return [_option_to_dict(opt) for opt in get_common_options()]
    except Exception:
        return []


def get_common_options_grouped():
    """Return common options grouped by category label."""
    try:
        from models.configs import get_common_options

        groups = {}
        for opt in get_common_options():
            cat_label = CATEGORY_LABELS.get(opt["category"], opt["category"])
            if cat_label not in groups:
                groups[cat_label] = {"label": cat_label, "fields": []}
            groups[cat_label]["fields"].append(_option_to_dict(opt))
        return list(groups.values())
    except Exception:
        return []


@bp.route("/config/<int:config_id>/versions")
def history(config_id):
    from models.configs import get_config, get_all_versions, get_latest_version
    from services.screen_manager import get_running_for_config

    config = get_config(config_id)
    if not config:
        flash("Config not found", "error")
        return redirect(url_for("index"))
    versions = get_all_versions(config_id)
    latest = get_latest_version(config_id)
    running_vid, _, running_is_this_config = get_running_for_config(
        config_id, versions
    )
    return render_template(
        "versions/history.html",
        config=config,
        versions=versions,
        latest_version_id=latest["id"] if latest else None,
        running_version_id=running_vid if running_is_this_config else None,
    )


@bp.route("/config/<int:config_id>/version/latest/edit", methods=["GET", "POST"])
def edit_latest(config_id):
    from models.configs import get_config, get_latest_version

    config = get_config(config_id)
    if not config:
        flash("Config not found", "error")
        return redirect(url_for("index"))
    version = get_latest_version(config_id)
    if not version:
        flash("No versions found", "error")
        return redirect(url_for("configs.view", config_id=config_id))
    return _edit_form(version, config)


@bp.route("/version/<int:version_id>/edit", methods=["GET", "POST"])
def edit(version_id):
    from models.configs import get_version

    version = get_version(version_id)
    if not version:
        flash("Version not found", "error")
        return redirect(url_for("index"))
    data = get_all_version_data(version_id)
    return _edit_form(version, None, data=data)


@bp.route("/version/<int:version_id>/fork-edit", methods=["GET", "POST"])
def fork_edit(version_id):
    from models.configs import get_version

    version = get_version(version_id)
    if not version:
        flash("Version not found", "error")
        return redirect(url_for("index"))

    source_data = get_all_version_data(version_id)
    session["fork_source_version_id"] = version_id
    session["fork_config_id"] = version["config_id"]
    session.pop("fork_version_id", None)

    fake_version = {
        "id": None,
        "config_id": version["config_id"],
        "config_name": version["config_name"],
        "version_number": "(New)",
        "comments": "",
        "status": None,
    }
    return _edit_form(fake_version, None, data=source_data, is_fork=True)


@bp.route("/version/<int:version_id>/delete", methods=["POST"])
def delete(version_id):
    from models.configs import get_version, delete_version
    from services.screen_manager import get_running_version_id

    version = get_version(version_id)
    if not version:
        flash("Version not found", "error")
        return redirect(url_for("index"))

    running_vid = get_running_version_id()
    if running_vid == version_id:
        flash("Cannot delete the currently running version. Stop it first.", "error")
        return redirect(url_for("configs.view", config_id=version["config_id"]))

    if not delete_version(version_id):
        flash("Failed to delete version", "error")
        return redirect(url_for("configs.view", config_id=version["config_id"]))

    flash(f"Version {version['version_number']} deleted", "success")
    return redirect(url_for("configs.view", config_id=version["config_id"]))


def _update_version_metadata(version_id, form):
    """Update comments and status for a version."""
    from models.base import get_conn

    with get_conn() as conn:
        with conn.cursor() as cur:
            status_val = form.get("status") or None
            cur.execute(
                "UPDATE config_versions SET comments = %s, status = %s WHERE id = %s",
                (form.get("comments", ""), status_val, version_id),
            )
            conn.commit()


def _convert_field_value(category, col, key, val):
    """Convert a form field value to its proper Python type."""
    if val == "" or val == "None":
        return None
    if col in _TRISTATE_COLS.get(category, set()):
        if val == "enable":
            return 1
        elif val == "disable":
            return 0
        else:
            return None
    if key.endswith("_bool") or col in _BOOL_COLS.get(category, set()):
        return 1 if val == "1" or val == "on" else 0
    return val


def _parse_category_data(form, category):
    """Parse form fields for a single category into a column->value dict."""
    prefix = f"{category}_"
    data = {}
    for key, val in form.items():
        if not key.startswith(prefix):
            continue
        col = key[len(prefix) :]
        is_password_edit = key.endswith("_edit") and val
        if is_password_edit:
            col = col[:-5]
        data[col] = _convert_field_value(category, col, key, val)
    return data


def _parse_complex_table_rows(form, table_name):
    """Parse form fields for a complex table into a list of row dicts."""
    rows = []
    ids_key = form.get(f"{table_name}_ids")
    if not ids_key:
        return rows
    row_ids = ids_key.split(",")
    for rid in row_ids:
        rid = rid.strip()
        if not rid:
            continue
        row = {}
        prefix = f"{table_name}_{rid}_"
        for key, val in form.items():
            if key.startswith(prefix):
                col = key[len(prefix) :]
                row[col] = val if val else None
        if row:
            rows.append(row)
    return rows


def _save_version_data(version_id, config_id, form_data=None):
    from models.configs import (
        CATEGORIES,
        COMPLEX_TABLES,
        save_category,
        save_complex_table,
    )

    form = form_data if form_data is not None else request.form

    _update_version_metadata(version_id, form)

    for cat in CATEGORIES:
        data = _parse_category_data(form, cat)
        if data:
            save_category(version_id, cat, data)

    for tbl in COMPLEX_TABLES:
        rows = _parse_complex_table_rows(form, tbl)
        save_complex_table(version_id, tbl, rows)


def _edit_form(version, config, data=None, is_fork=False):
    from models.configs import CATEGORIES, COMPLEX_TABLES

    if request.method == "POST":
        if is_fork:
            source_vid = session.pop("fork_source_version_id", None)
            config_id = session.pop("fork_config_id", None)
            new_vid = duplicate_version(
                source_vid, config_id, request.form.get("comments", "")
            )
            session["fork_version_id"] = new_vid

            _save_version_data(new_vid, config_id, request.form)
            flash("Version saved", "success")
            return redirect(url_for("configs.view", config_id=config_id))
        else:
            # Existing version edit
            _save_version_data(version["id"], version["config_id"], request.form)
            flash("Version saved", "success")
            return redirect(url_for("configs.view", config_id=version["config_id"]))

    if data is None:
        data = get_all_version_data(version["id"])

    categories = CATEGORIES
    complex_tables = COMPLEX_TABLES

    # Determine which version of this config is currently running
    from models.configs import get_all_versions
    from services.screen_manager import get_running_for_config

    all_versions = get_all_versions(version["config_id"])
    running_vid, running_version, _ = get_running_for_config(
        version["config_id"], all_versions
    )

    return render_template(
        "versions/form.html",
        version=version,
        config=config,
        data=data,
        categories=categories,
        complex_tables=complex_tables,
        category_labels=CATEGORY_LABELS,
        running_version_id=running_vid,
        running_version=running_version,
        is_fork=is_fork,
        common_option_ids=get_common_option_set(),
        common_options_list=get_common_options_list(),
        common_options_grouped=get_common_options_grouped(),
    )


@bp.route("/version/<int:version_id>/duplicate", methods=["POST"])
def duplicate(version_id):
    from models.configs import get_version, duplicate_version

    version = get_version(version_id)
    if not version:
        flash("Version not found", "error")
        return redirect(url_for("index"))

    new_vid = duplicate_version(version_id, version["config_id"], "Duplicated")
    flash("Version duplicated", "success")
    return redirect(url_for("versions.edit", version_id=new_vid))


@bp.route("/version/<int:version_id>/command")
def command(version_id):
    from services.command_builder import build_command_string

    cmd = build_command_string(version_id, redact_secrets=True)
    return jsonify({"command": cmd})


# Boolean columns per category (simple on/off checkboxes)
_BOOL_COLS = {
    "context_batching": {"context_shift", "special_tokens", "warmup", "spm_infill"},
    "cpu_threading": {"cpu_strict", "cpu_strict_batch", "poll_batch"},
    "gpu_device": {"no_host", "cpu_moe", "cpu_moe_draft"},
    "memory": {"mlock"},
    "sampling": {"ignore_eos", "backend_sampling"},
    "server": {
        "reuse_port",
        "embedding",
        "reranking",
        "metrics",
        "props",
        "lora_init_without_apply",
    },
    "chat_templates": {},
    "checkpoints": {},
    "logging": {
        "log_prefix",
        "log_timestamps",
        "verbose",
        "log_disable",
        "offline",
        "perf",
        "escape",
    },
}

# Tri-state columns per category (enable/disable/default via select)
_TRISTATE_COLS = {
    "model_loading": {"mmproj_auto", "mmproj_offload"},
    "context_batching": {"cont_batching", "cache_prompt"},
    "gpu_device": {"kv_offload", "repack", "op_offload"},
    "memory": {"mmap", "direct_io"},
    "server": {"webui", "slots"},
    "chat_templates": {"jinja", "skip_chat_parsing", "prefill_assistant"},
    "checkpoints": {"kv_unified", "cache_idle_slots"},
}


