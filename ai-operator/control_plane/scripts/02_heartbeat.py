from datetime import datetime
from pathlib import Path

from _script_env import setup_import_path

setup_import_path()

from control_plane.runtime import (
    check_in_node,
    connect_db,
    dispatch_queued_jobs,
    ensure_runtime_dirs,
    fetch_jobs,
    fetch_online_nodes,
    import_legacy_jobs,
    load_config,
    local_node_config,
    mark_stale_nodes,
    repo_root,
    seed_nodes,
    write_legacy_snapshot,
)


def _write_approval_template(approvals_path: Path, jobs: list[dict]) -> None:
    if not jobs:
        return
    if approvals_path.exists() and approvals_path.stat().st_size > 0:
        return
    job = jobs[0]
    with open(approvals_path, 'w', encoding='utf-8') as handle:
        handle.write(f"## Approval Needed for {job['name']}\n\n")
        handle.write(f"- **Action requested:** {job['command'] or 'Review attached metadata'}\n")
        handle.write(f"- **Reason:** {job['metadata'].get('reason', 'Human approval required before dispatch')}\n")
        handle.write(f"- **Exact command or change proposed:** {job['command'] or 'See job metadata'}\n")
        handle.write(f"- **Rollback path:** {job['metadata'].get('rollback', 'Return job to queued or cancel it')}\n")
        handle.write(f"- **Deadline/urgency:** {job['metadata'].get('urgency', 'Not specified')}\n")
        handle.write(f"- **Affected systems:** {job['metadata'].get('affected_systems', 'Not specified')}\n")


def check_heartbeat():
    root = repo_root()
    paths = ensure_runtime_dirs(root)
    config = load_config(root)
    conn = connect_db(root, config)
    seed_nodes(conn, config)
    imported = import_legacy_jobs(conn, root)

    local = local_node_config(config)
    check_in_node(
        conn,
        local["id"],
        display_name=local.get("display_name", local["id"]),
        role=local.get("role", "control-plane"),
        transport=local.get("transport", "local"),
        address=local.get("address", "127.0.0.1"),
        capabilities=local.get("capabilities", []),
        notes="Heartbeat check-in",
    )

    stale_after = int(config.get("dispatcher", {}).get("stale_after_seconds", 900))
    stale_marked = mark_stale_nodes(conn, stale_after)
    assignments = dispatch_queued_jobs(conn, config)
    awaiting_approval = fetch_jobs(conn, statuses=["awaiting_approval"])
    _write_approval_template(paths["logs"] / "approvals_needed.md", awaiting_approval)
    snapshot_path = write_legacy_snapshot(conn, root)

    timestamp = datetime.now().isoformat()
    online_nodes = fetch_online_nodes(conn)
    queued_jobs = fetch_jobs(conn, statuses=["queued"])
    assigned_jobs = fetch_jobs(conn, statuses=["assigned"])
    failed_jobs = fetch_jobs(conn, statuses=["failed"])
    msg = (
        f"[{timestamp}] Heartbeat tick. "
        f"online_nodes={len(online_nodes)} queued={len(queued_jobs)} "
        f"assigned={len(assigned_jobs)} awaiting_approval={len(awaiting_approval)} "
        f"failed={len(failed_jobs)} imported_legacy={imported} "
        f"stale_nodes_marked_offline={stale_marked} assignments={len(assignments)} "
        f"snapshot={snapshot_path}"
    )

    with open(paths["logs"] / "heartbeat.log", 'a', encoding='utf-8') as handle:
        handle.write(msg + "\n")

    print(msg)

if __name__ == "__main__":
    check_heartbeat()
