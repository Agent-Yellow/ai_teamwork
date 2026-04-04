import argparse

from _script_env import setup_import_path

setup_import_path()

from control_plane.runtime import (
    connect_db,
    ensure_runtime_dirs,
    load_config,
    repo_root,
    seed_nodes,
    update_job_status,
    write_legacy_snapshot,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update a dispatcher job status.")
    parser.add_argument("--job-id", required=True, help="Job id to update.")
    parser.add_argument(
        "--status",
        required=True,
        choices=["queued", "assigned", "running", "failed", "retryable", "awaiting_approval", "completed"],
        help="New job status.",
    )
    parser.add_argument("--node-id", help="Associated node id.")
    parser.add_argument("--message", help="Optional event detail.")
    args = parser.parse_args()

    root = repo_root()
    ensure_runtime_dirs(root)
    config = load_config(root)
    conn = connect_db(root, config)
    seed_nodes(conn, config)

    update_job_status(conn, args.job_id, args.status, node_id=args.node_id, detail=args.message)
    write_legacy_snapshot(conn, root)
    print(f"Updated {args.job_id} to {args.status}")


if __name__ == "__main__":
    main()
