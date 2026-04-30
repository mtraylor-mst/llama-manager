from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify

bp = Blueprint('versions', __name__)


@bp.route('/config/<int:config_id>/versions')
def history(config_id):
    from models.configs import get_config, get_all_versions, get_latest_version
    from services.screen_manager import get_running_version_id
    config = get_config(config_id)
    if not config:
        flash('Config not found', 'error')
        return redirect(url_for('index'))
    versions = get_all_versions(config_id)
    latest = get_latest_version(config_id)
    running_vid = get_running_version_id()
    running_is_this_config = any(v['id'] == running_vid for v in versions) if running_vid else False
    return render_template(
        'versions/history.html',
        config=config,
        versions=versions,
        latest_version_id=latest['id'] if latest else None,
        running_version_id=running_vid if running_is_this_config else None,
    )


@bp.route('/config/<int:config_id>/version/latest/edit', methods=['GET', 'POST'])
def edit_latest(config_id):
    from models.configs import get_config, get_latest_version
    config = get_config(config_id)
    if not config:
        flash('Config not found', 'error')
        return redirect(url_for('index'))
    version = get_latest_version(config_id)
    if not version:
        flash('No versions found', 'error')
        return redirect(url_for('configs.view', config_id=config_id))
    return _edit_form(version, config)


@bp.route('/version/<int:version_id>/edit', methods=['GET', 'POST'])
def edit(version_id):
    from models.configs import get_version
    version = get_version(version_id)
    if not version:
        flash('Version not found', 'error')
        return redirect(url_for('index'))
    return _edit_form(version, None)


def _edit_form(version, config):
    from models.configs import CATEGORIES, COMPLEX_TABLES, get_all_version_data, save_category, save_complex_table

    if request.method == 'POST':
        # Save comments and status
        from models.base import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                status_val = request.form.get('status') or None
                cur.execute(
                    'UPDATE config_versions SET comments = %s, status = %s WHERE id = %s',
                    (request.form.get('comments', ''), status_val, version['id']),
                )
                conn.commit()

        # Save each category
        for cat in CATEGORIES:
            prefix = f'{cat}_'
            data = {}
            for key, val in request.form.items():
                if key.startswith(prefix):
                    col = key[len(prefix):]
                    # Convert empty strings to None
                    if val == '' or val == 'None':
                        data[col] = None
                    elif key.endswith('_bool') or col in _BOOL_COLS.get(cat, set()):
                        data[col] = 1 if val == '1' or val == 'on' else 0
                    else:
                        data[col] = val
            if data:
                save_category(version['id'], cat, data)

        # Save complex tables
        for tbl in COMPLEX_TABLES:
            rows = []
            ids_key = request.form.get(f'{tbl}_ids')
            if ids_key:
                row_ids = ids_key.split(',')
                for rid in row_ids:
                    rid = rid.strip()
                    if not rid:
                        continue
                    row = {}
                    for key, val in request.form.items():
                        if key.startswith(f'{tbl}_{rid}_'):
                            col = key[len(f'{tbl}_{rid}_'):]
                            row[col] = val if val else None
                    if row:
                        rows.append(row)
            save_complex_table(version['id'], tbl, rows)

        flash('Version saved', 'success')
        return redirect(url_for('configs.view', config_id=version['config_id']))

    data = get_all_version_data(version['id'])
    categories = CATEGORIES
    complex_tables = COMPLEX_TABLES

    # Determine which version of this config is currently running
    from services.screen_manager import get_running_version_id
    from models.configs import get_all_versions
    running_vid = get_running_version_id()
    all_versions = get_all_versions(version['config_id'])
    running_version = None
    if running_vid:
        for v in all_versions:
            if v['id'] == running_vid:
                running_version = v
                break

    return render_template(
        'versions/form.html',
        version=version,
        config=config,
        data=data,
        categories=categories,
        complex_tables=complex_tables,
        category_labels=CATEGORY_LABELS,
        running_version_id=running_vid,
        running_version=running_version,
    )


@bp.route('/version/<int:version_id>/fork-edit', methods=['GET'])
def fork_edit(version_id):
    from models.configs import get_version, duplicate_version
    version = get_version(version_id)
    if not version:
        flash('Version not found', 'error')
        return redirect(url_for('index'))

    new_vid = duplicate_version(version_id, version['config_id'], '')
    return redirect(url_for('versions.edit', version_id=new_vid))


@bp.route('/version/<int:version_id>/duplicate', methods=['POST'])
def duplicate(version_id):
    from models.configs import get_version, duplicate_version
    version = get_version(version_id)
    if not version:
        flash('Version not found', 'error')
        return redirect(url_for('index'))

    new_vid = duplicate_version(version_id, version['config_id'], 'Duplicated')
    flash('Version duplicated', 'success')
    return redirect(url_for('versions.edit', version_id=new_vid))


@bp.route('/version/<int:version_id>/command')
def command(version_id):
    from services.command_builder import build_command
    cmd = build_command(version_id)
    return jsonify({'command': cmd})


# Boolean columns per category
_BOOL_COLS = {
    'context_batching': {'cont_batching', 'context_shift', 'special_tokens', 'warmup',
                         'spm_infill', 'cache_prompt'},
    'cpu_threading': {'cpu_strict', 'cpu_strict_batch', 'poll_batch'},
    'gpu_device': {'kv_offload', 'repack', 'no_host', 'op_offload', 'cpu_moe',
                   'cpu_moe_draft'},
    'memory': {'mmap', 'mlock', 'direct_io'},
    'sampling': {'ignore_eos', 'backend_sampling'},
    'server': {'reuse_port', 'webui', 'embedding', 'reranking', 'metrics',
               'props', 'slots', 'lora_init_without_apply'},
    'chat_templates': {'jinja', 'skip_chat_parsing', 'prefill_assistant'},
    'checkpoints': {'kv_unified', 'cache_idle_slots'},
    'logging': {'log_prefix', 'log_timestamps', 'verbose', 'log_disable',
                'offline', 'perf', 'escape'},
}

CATEGORY_LABELS = {
    'model_loading': 'Model Loading',
    'context_batching': 'Context & Batching',
    'cpu_threading': 'CPU / Threading',
    'gpu_device': 'GPU / Device',
    'memory': 'Memory',
    'sampling': 'Sampling',
    'server': 'Server',
    'speculative': 'Speculative Decoding',
    'chat_templates': 'Chat & Templates',
    'checkpoints': 'Checkpoints & Cache',
    'logging': 'Logging',
    'advanced': 'Advanced / Override',
}
