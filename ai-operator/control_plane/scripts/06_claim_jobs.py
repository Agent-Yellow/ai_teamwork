import argparse
import json

from _script_env import setup_import_path

setup_import_path()

from control_plane.runtime import (
    connect_db,
    ensure_runtime_dirs,
    fetch_jobs,
    load_config,
    local_node_config,
    repo_root,
    seed_nodes,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="List dispatcher jobs assigned to a node.")
    parser.add_argument("--node-id", help="Node id. Defaults to local_node.id from config.")
    args = parser.parse_args()

    root = repo_root()
    ensure_runtime_dirs(root)
    config = load_config(root)
    conn = connect_db(root, config)
    seed_nodes(conn, config)

    node_id = args.node_id or local_node_config(config)["id"]
    jobs = [job for job in fetch_jobs(conn, statuses=["assigned", "running"]) if job["assigned_node"] == node_id]
    print(json.dumps(jobs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
