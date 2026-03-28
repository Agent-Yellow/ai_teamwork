import json

from _script_env import setup_import_path

setup_import_path()

from control_plane.executor import execute_assigned_jobs, refresh_node_statuses
from control_plane.runtime import connect_db, ensure_runtime_dirs, load_config, repo_root, seed_nodes, write_legacy_snapshot


def main() -> None:
    root = repo_root()
    ensure_runtime_dirs(root)
    config = load_config(root)
    conn = connect_db(root, config)
    seed_nodes(conn, config)
    refresh_node_statuses(conn, config)
    results = execute_assigned_jobs(conn, config)
    write_legacy_snapshot(conn, root)
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
