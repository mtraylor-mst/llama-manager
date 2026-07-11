"""Config usage analytics — track launch/stop sessions."""

from models.base import get_conn


def record_launch(version_id):
    """Record a server launch. Returns the usage record id."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO config_usage (version_id) VALUES (%s)",
                (version_id,),
            )
            conn.commit()
            return cur.lastrowid


def record_stop(exit_reason=None):
    """Close the most recent open session. Returns True if a session was found."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM config_usage WHERE stopped_at IS NULL "
                "ORDER BY launched_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            if not row:
                return False
            cur.execute(
                "UPDATE config_usage SET stopped_at = CURRENT_TIMESTAMP, "
                "exit_reason = %s WHERE id = %s",
                (exit_reason, row["id"]),
            )
            conn.commit()
            return True


def get_usage_stats():
    """Get aggregated usage statistics per config.

    Returns list of dicts with:
      - config_id, config_name, total_launches, unique_versions
      - avg_runtime_sec (average seconds between launch and stop)
      - last_launched_at
      - exit_reasons: dict of reason -> count
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get per-config stats
            cur.execute(
                "SELECT cv.config_id, c.name as config_name, "
                "COUNT(u.id) as total_launches, "
                "COUNT(DISTINCT u.version_id) as unique_versions, "
                "AVG(TIMESTAMPDIFF(SECOND, u.launched_at, u.stopped_at)) as avg_runtime_sec, "
                "MAX(u.launched_at) as last_launched_at "
                "FROM config_usage u "
                "JOIN config_versions cv ON cv.id = u.version_id "
                "JOIN configs c ON c.id = cv.config_id "
                "GROUP BY cv.config_id, c.name "
                "ORDER BY total_launches DESC"
            )
            stats = cur.fetchall()

            # Get exit reason breakdown per config
            cur.execute(
                "SELECT cv.config_id, u.exit_reason, COUNT(*) as cnt "
                "FROM config_usage u "
                "JOIN config_versions cv ON cv.id = u.version_id "
                "WHERE u.stopped_at IS NOT NULL "
                "GROUP BY cv.config_id, u.exit_reason"
            )
            reasons_rows = cur.fetchall()

            # Build reason dict per config
            reasons_by_config = {}
            for row in reasons_rows:
                cid = row["config_id"]
                if cid not in reasons_by_config:
                    reasons_by_config[cid] = {}
                reason = row["exit_reason"] or "unknown"
                reasons_by_config[cid][reason] = (
                    reasons_by_config[cid].get(reason, 0) + row["cnt"]
                )

            for stat in stats:
                stat["avg_runtime_sec"] = (
                    round(stat["avg_runtime_sec"]) if stat["avg_runtime_sec"] else None
                )
                stat["exit_reasons"] = reasons_by_config.get(stat["config_id"], {})

            return stats


def get_recent_sessions(limit=50):
    """Get recent launch/stop sessions ordered by launch time."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.version_id, cv.config_id, c.name as config_name, "
                "cv.version_number, u.launched_at, u.stopped_at, u.exit_reason "
                "FROM config_usage u "
                "JOIN config_versions cv ON cv.id = u.version_id "
                "JOIN configs c ON c.id = cv.config_id "
                "ORDER BY u.launched_at DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()


def get_running_session_count():
    """Count sessions that haven't been stopped yet."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM config_usage WHERE stopped_at IS NULL"
            )
            return cur.fetchone()["cnt"]
