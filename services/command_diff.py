import shlex

from services.command_builder import build_command


def _parse_command_to_dict(args):
    """Parse a flat command list into a dict of flag -> value for easy diffing."""
    result = {}
    i = 0
    current_flag = None
    while i < len(args):
        arg = args[i]
        if arg.startswith("-"):
            if current_flag:
                pass
            current_flag = arg
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                result[current_flag] = args[i + 1]
                i += 2
                continue
            else:
                result[current_flag] = True
        elif current_flag:
            result[current_flag] = str(result.get(current_flag, [])) + " " + arg
        i += 1
    return result


def diff_commands(version_id_1, version_id_2):
    """Compare commands between two versions.

    Returns a dict with:
        - version_1: {id, version_number, config_name}
        - version_2: {id, version_number, config_name}
        - added: flags in v2 but not v1 (list of {flag, value})
        - removed: flags in v1 but not v2 (list of {flag, value})
        - changed: flags with different values (list of {flag, old_value, new_value})
        - command_1: full command string for v1
        - command_2: full command string for v2
    """
    from models.configs import get_version

    cmd1 = build_command(version_id_1)
    cmd2 = build_command(version_id_2)

    cmd1_str = " ".join(shlex.quote(a) for a in cmd1)
    cmd2_str = " ".join(shlex.quote(a) for a in cmd2)

    flags1 = _parse_command_to_dict(cmd1)
    flags2 = _parse_command_to_dict(cmd2)

    all_flags = set(flags1.keys()) | set(flags2.keys())

    added = []
    removed = []
    changed = []

    for flag in sorted(all_flags):
        in_1 = flag in flags1
        in_2 = flag in flags2

        if in_1 and not in_2:
            removed.append(
                {
                    "flag": flag,
                    "value": flags1[flag] if flags1[flag] is not True else None,
                }
            )
        elif in_2 and not in_1:
            added.append(
                {
                    "flag": flag,
                    "value": flags2[flag] if flags2[flag] is not True else None,
                }
            )
        elif flags1[flag] != flags2[flag]:
            changed.append(
                {
                    "flag": flag,
                    "old_value": flags1[flag] if flags1[flag] is not True else None,
                    "new_value": flags2[flag] if flags2[flag] is not True else None,
                }
            )

    v1 = get_version(version_id_1)
    v2 = get_version(version_id_2)

    return {
        "version_1": {
            "id": version_id_1,
            "version_number": v1["version_number"] if v1 else "?",
            "config_name": v1["config_name"] if v1 else "?",
        },
        "version_2": {
            "id": version_id_2,
            "version_number": v2["version_number"] if v2 else "?",
            "config_name": v2["config_name"] if v2 else "?",
        },
        "added": added,
        "removed": removed,
        "changed": changed,
        "command_1": cmd1_str,
        "command_2": cmd2_str,
    }
