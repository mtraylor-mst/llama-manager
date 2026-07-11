"""Database access for config templates."""

from models.base import get_conn
from models.configs import (
    CATEGORIES,
    COMPLEX_TABLES,
    create_config,
    create_version,
    save_category,
    save_complex_table,
    get_all_version_data,
)


def get_all_templates():
    """Get all templates with source version info."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ct.*, cv.version_number as source_version_number, "
                "c.name as source_config_name "
                "FROM config_templates ct "
                "JOIN config_versions cv ON cv.id = ct.source_version_id "
                "JOIN configs c ON c.id = cv.config_id "
                "ORDER BY ct.name"
            )
            return cur.fetchall()


def get_template(template_id):
    """Get a single template with source info."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ct.*, cv.version_number as source_version_number, "
                "c.name as source_config_name "
                "FROM config_templates ct "
                "JOIN config_versions cv ON cv.id = ct.source_version_id "
                "JOIN configs c ON c.id = cv.config_id "
                "WHERE ct.id = %s",
                (template_id,),
            )
            return cur.fetchone()


def create_template(name, description, source_version_id):
    """Create a new template from an existing version."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO config_templates (name, description, source_version_id) "
                "VALUES (%s, %s, %s)",
                (name, description, source_version_id),
            )
            conn.commit()
            return cur.lastrowid


def update_template(template_id, name, description):
    """Update template metadata."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE config_templates SET name=%s, description=%s WHERE id=%s",
                (name, description, template_id),
            )
            conn.commit()


def delete_template(template_id):
    """Delete a template. CASCADE handles variables."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM config_templates WHERE id = %s", (template_id,))
            conn.commit()
            return cur.rowcount > 0


def get_template_variables(template_id):
    """Get all variables for a template, ordered."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM template_variables "
                "WHERE template_id = %s ORDER BY display_order",
                (template_id,),
            )
            return cur.fetchall()


def save_template_variables(template_id, variables):
    """Save variables for a template. variables is a list of dicts."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM template_variables WHERE template_id = %s",
                (template_id,),
            )
            for i, var in enumerate(variables):
                cur.execute(
                    "INSERT INTO template_variables "
                    "(template_id, variable_name, display_label, default_value, hint, display_order) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        template_id,
                        var.get("variable_name", ""),
                        var.get("display_label", ""),
                        var.get("default_value", ""),
                        var.get("hint", ""),
                        i,
                    ),
                )
            conn.commit()


def instantiate_template(template_id, config_name, variable_values=None):
    """Create a new config from a template with variable substitutions.

    Args:
        template_id: The template to instantiate from.
        config_name: Name for the new config.
        variable_values: Dict of variable_name -> value to substitute.

    Returns:
        Tuple of (config_id, version_id).
    """
    variable_values = variable_values or {}

    # Get source version data
    template = get_template(template_id)
    if not template:
        return None, None

    source_data = get_all_version_data(template["source_version_id"])

    # Build variable substitution map
    var_map = {}
    for var_name, var_value in variable_values.items():
        placeholder = f"{{{{{var_name}}}}}"
        var_map[placeholder] = var_value

    # Create new config and version
    config_id = create_config(config_name)
    version_id = create_version(config_id)

    # Copy and substitute category data
    for cat in CATEGORIES:
        row = dict(source_data.get(cat, {}))
        if row:
            row.pop("version_id", None)
            for placeholder, value in var_map.items():
                row = {k: (v.replace(placeholder, value) if isinstance(v, str) else v)
                       for k, v in row.items()}
            save_category(version_id, cat, row)

    # Copy complex tables with substitution
    for tbl in COMPLEX_TABLES:
        rows = source_data.get(tbl, [])
        if rows:
            substituted = []
            for row in rows:
                new_row = {}
                for k, v in row.items():
                    if k in ("id", "version_id"):
                        continue
                    if isinstance(v, str):
                        for placeholder, value in var_map.items():
                            v = v.replace(placeholder, value)
                    new_row[k] = v
                substituted.append(new_row)
            save_complex_table(version_id, tbl, substituted)

    return config_id, version_id
