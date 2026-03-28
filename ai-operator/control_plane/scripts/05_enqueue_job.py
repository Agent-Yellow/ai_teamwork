import argparse

from _script_env import setup_import_path

setup_import_path()

from control_plane.policy import (
    available_job_types,
    default_job_type,
    job_defaults,
    validate_job_command,
    retryable_default,
)
from control_plane.runtime import (
    connect_db,
    enqueue_job,
    ensure_runtime_dirs,
    load_config,
    normalize_capabilities,
    repo_root,
    seed_nodes,
    write_legacy_snapshot,
)


def main() -> None:
    root = repo_root()
    config = load_config(root)
    parser = argparse.ArgumentParser(description="Queue a dispatcher job.")
    parser.add_argument("--name", required=True, help="Job name.")
    parser.add_argument("--command", required=True, help="Command or action to run.")
    parser.add_argument(
        "--job-type",
        default=default_job_type(config),
        choices=available_job_types(config),
        help="Policy-controlled job type.",
    )
    parser.add_argument("--requires", default="", help="Comma-separated required capabilities.")
    parser.add_argument("--preferred-node", help="Preferred node id.")
    parser.add_argument("--reason", help="Why the job exists.")
    parser.add_argument("--rollback", help="Rollback notes.")
    parser.add_argument("--urgency", help="Urgency note.")
    parser.add_argument("--affected-systems", help="Affected systems note.")
    parser.add_argument("--approval-required", action="store_true", help="Route the job into approval first.")
    parser.add_argument("--retryable-on-failure", action="store_true", help="Allow heartbeat to retry the job after failures.")
    args = parser.parse_args()

    ensure_runtime_dirs(root)
    conn = connect_db(root, config)
    seed_nodes(conn, config)

    validate_job_command(config, args.job_type, args.command)
    required_capabilities, approval_required, preferred_node = job_defaults(
        config,
        args.job_type,
        required_capabilities=normalize_capabilities(args.requires),
        approval_required=args.approval_required,
        preferred_node=args.preferred_node,
    )
    retryable_on_failure = args.retryable_on_failure or retryable_default(config, args.job_type)

    metadata = {
        "job_type": args.job_type,
        "preferred_node": preferred_node,
        "reason": args.reason,
        "rollback": args.rollback,
        "retryable_on_failure": retryable_on_failure,
        "urgency": args.urgency,
        "affected_systems": args.affected_systems,
    }
    metadata = {key: value for key, value in metadata.items() if value}
    job_id = enqueue_job(
        conn,
        name=args.name,
        command=args.command,
        required_capabilities=required_capabilities,
        metadata=metadata,
        approval_required=approval_required,
    )
    write_legacy_snapshot(conn, root)
    print(f"Queued job {job_id}")


if __name__ == "__main__":
    main()
