import argparse

from _script_env import setup_import_path

setup_import_path()

from control_plane.runtime import (
    check_in_node,
    connect_db,
    ensure_runtime_dirs,
    fetch_node,
    load_config,
    local_node_config,
    normalize_capabilities,
    node_config,
    repo_root,
    seed_nodes,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Register or refresh a node heartbeat.")
    parser.add_argument("--node-id", help="Node identifier. Defaults to local_node.id from config.")
    parser.add_argument("--display-name", help="Human-friendly node label.")
    parser.add_argument("--role", help="Node role, e.g. control-plane or worker.")
    parser.add_argument("--transport", help="Transport, e.g. local, ssh, tailscale.")
    parser.add_argument("--address", help="Reachable address or tailnet IP.")
    parser.add_argument("--capabilities", help="Comma-separated capabilities.")
    parser.add_argument("--notes", help="Optional note to persist with the check-in.")
    args = parser.parse_args()

    root = repo_root()
    ensure_runtime_dirs(root)
    config = load_config(root)
    conn = connect_db(root, config)
    seed_nodes(conn, config)

    local = local_node_config(config)
    node_id = args.node_id or local["id"]
    display_name = args.display_name or local.get("display_name", node_id)
    role = args.role or local.get("role", "worker")
    transport = args.transport or local.get("transport", "tailscale")
    address = args.address or local.get("address", "")
    capabilities = normalize_capabilities(args.capabilities) or normalize_capabilities(local.get("capabilities"))
    configured = node_config(config, node_id) or {}
    existing = fetch_node(conn, node_id) or {}
    metadata = configured.get("metadata") or existing.get("metadata") or {}

    check_in_node(
        conn,
        node_id,
        display_name=display_name,
        role=role,
        transport=transport,
        address=address,
        capabilities=capabilities,
        metadata=metadata,
        notes=args.notes,
    )
    print(f"Node {node_id} checked in with capabilities={','.join(capabilities)}")


if __name__ == "__main__":
    main()
