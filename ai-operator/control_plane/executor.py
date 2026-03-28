from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from control_plane.runtime import (
    check_in_node,
    configured_nodes,
    fetch_jobs,
    fetch_node,
    fetch_nodes,
    iso_now,
    local_node_config,
    merge_job_metadata,
    normalize_capabilities,
    record_event,
    repo_root,
    update_job_status,
)


def _node_metadata(node: dict[str, Any]) -> dict[str, Any]:
    return node.get("metadata", {}) or {}


def _local_node_id(config: dict[str, Any]) -> str:
    return local_node_config(config)["id"]


def is_local_node(config: dict[str, Any], node: dict[str, Any]) -> bool:
    return node["id"] == _local_node_id(config) or node.get("transport") == "local"


def ssh_target(node: dict[str, Any]) -> str:
    metadata = _node_metadata(node)
    explicit = metadata.get("ssh_target")
    if explicit:
        return explicit
    user = metadata.get("ssh_user")
    address = node.get("address") or ""
    return f"{user}@{address}" if user else address


def ssh_command_prefix(node: dict[str, Any], *, timeout_seconds: int) -> list[str]:
    metadata = _node_metadata(node)
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={metadata.get('ssh_connect_timeout_seconds', timeout_seconds)}",
    ]
    if metadata.get("ssh_port"):
        command.extend(["-p", str(metadata["ssh_port"])])
    if metadata.get("ssh_identity_file"):
        command.extend(["-i", str(Path(metadata["ssh_identity_file"]).expanduser())])
    command.append(ssh_target(node))
    return command


def _remote_shell_command(node: dict[str, Any], raw_command: str) -> str:
    metadata = _node_metadata(node)
    workdir = metadata.get("workdir")
    if workdir:
        return f"cd {shlex.quote(workdir)} && {raw_command}"
    return raw_command


def probe_node(conn, config: dict[str, Any], node: dict[str, Any]) -> tuple[bool, str]:
    node_id = node["id"]
    display_name = node.get("display_name", node_id)
    role = node.get("role", "worker")
    transport = node.get("transport", "local")
    address = node.get("address", "")
    capabilities = normalize_capabilities(node.get("capabilities"))
    metadata = _node_metadata(node)
    probe_timeout = int(config.get("dispatcher", {}).get("probe_timeout_seconds", 15))

    if is_local_node(config, node):
        check_in_node(
            conn,
            node_id,
            display_name=display_name,
            role=role,
            transport="local",
            address=address or "127.0.0.1",
            capabilities=capabilities,
            metadata=metadata,
            notes="Local Mac dispatcher host",
            status="online",
        )
        return True, "local"

    target = ssh_target(node)
    if not target:
        check_in_node(
            conn,
            node_id,
            display_name=display_name,
            role=role,
            transport=transport,
            address=address,
            capabilities=capabilities,
            metadata=metadata,
            notes="Missing SSH target",
            status="offline",
        )
        return False, "missing ssh target"

    probe = metadata.get("probe_command", "printf ready")
    command = ssh_command_prefix(node, timeout_seconds=probe_timeout) + [
        f"bash -lc {shlex.quote(probe)}"
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=probe_timeout,
            check=False,
        )
    except Exception as exc:
        check_in_node(
            conn,
            node_id,
            display_name=display_name,
            role=role,
            transport=transport,
            address=address,
            capabilities=capabilities,
            metadata=metadata,
            notes=f"Probe failed: {exc}",
            status="offline",
        )
        return False, str(exc)

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if result.returncode == 0:
        detail = stdout or "ssh-ok"
        check_in_node(
            conn,
            node_id,
            display_name=display_name,
            role=role,
            transport=transport,
            address=address,
            capabilities=capabilities,
            metadata=metadata,
            notes=detail,
            status="online",
        )
        return True, detail

    detail = stderr or stdout or f"ssh exited {result.returncode}"
    check_in_node(
        conn,
        node_id,
        display_name=display_name,
        role=role,
        transport=transport,
        address=address,
        capabilities=capabilities,
        metadata=metadata,
        notes=detail,
        status="offline",
    )
    return False, detail


def refresh_node_statuses(conn, config: dict[str, Any]) -> list[tuple[str, bool, str]]:
    results = []
    for node in configured_nodes(config):
        ok, detail = probe_node(conn, config, node)
        results.append((node["id"], ok, detail))
    return results


def _local_execution_command(command: str, node: dict[str, Any]) -> tuple[list[str], Path | None]:
    metadata = _node_metadata(node)
    workdir = Path(metadata["workdir"]).expanduser() if metadata.get("workdir") else None
    return ["/bin/zsh", "-lc", command], workdir


def _remote_execution_command(command: str, node: dict[str, Any], timeout_seconds: int) -> tuple[list[str], None]:
    remote = _remote_shell_command(node, command)
    full = ssh_command_prefix(node, timeout_seconds=timeout_seconds) + [
        f"bash -lc {shlex.quote(remote)}"
    ]
    return full, None


def _write_job_log(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True))
        handle.write("\n")


def execute_assigned_jobs(conn, config: dict[str, Any]) -> list[dict[str, Any]]:
    root = repo_root()
    job_log_dir = root / "logs" / "jobs"
    results: list[dict[str, Any]] = []
    execution_timeout = int(config.get("dispatcher", {}).get("execution_timeout_seconds", 1800))

    online = {node["id"]: node for node in fetch_nodes(conn) if node.get("status") == "online"}
    for job in fetch_jobs(conn, statuses=["assigned"]):
        node_id = job["assigned_node"]
        if not node_id or node_id not in online:
            continue
        node = online[node_id]
        metadata = dict(job["metadata"])
        timeout = int(metadata.get("timeout_seconds", execution_timeout))
        update_job_status(conn, job["id"], "running", node_id=node_id, detail="Execution started")

        started_at = iso_now()
        log_path = job_log_dir / f"{job['id']}.json"
        try:
            if is_local_node(config, node):
                command, cwd = _local_execution_command(job["command"], node)
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    cwd=str(cwd) if cwd else None,
                )
            else:
                command, _ = _remote_execution_command(job["command"], node, timeout)
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            payload = {
                "job_id": job["id"],
                "job_name": job["name"],
                "node_id": node_id,
                "started_at": started_at,
                "completed_at": iso_now(),
                "command": job["command"],
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
            _write_job_log(log_path, payload)
            merge_job_metadata(
                conn,
                job["id"],
                {
                    "last_execution": {
                        "node_id": node_id,
                        "started_at": started_at,
                        "completed_at": payload["completed_at"],
                        "returncode": completed.returncode,
                        "log_path": str(log_path),
                    }
                },
            )
            if completed.returncode == 0:
                update_job_status(conn, job["id"], "completed", node_id=node_id, detail=str(log_path))
                results.append({"job_id": job["id"], "status": "completed", "node_id": node_id})
                continue

            failure_status = "retryable" if metadata.get("retryable_on_failure") else "failed"
            update_job_status(
                conn,
                job["id"],
                failure_status,
                node_id=node_id,
                detail=f"returncode={completed.returncode} log={log_path}",
            )
            if completed.returncode == 255 and not is_local_node(config, node):
                probe_node(conn, config, node)
            results.append({"job_id": job["id"], "status": failure_status, "node_id": node_id})
        except subprocess.TimeoutExpired as exc:
            payload = {
                "job_id": job["id"],
                "job_name": job["name"],
                "node_id": node_id,
                "started_at": started_at,
                "completed_at": iso_now(),
                "command": job["command"],
                "timeout_seconds": timeout,
                "stdout": exc.stdout,
                "stderr": exc.stderr,
                "error": "timeout",
            }
            _write_job_log(log_path, payload)
            merge_job_metadata(
                conn,
                job["id"],
                {
                    "last_execution": {
                        "node_id": node_id,
                        "started_at": started_at,
                        "completed_at": payload["completed_at"],
                        "timeout_seconds": timeout,
                        "log_path": str(log_path),
                    }
                },
            )
            update_job_status(conn, job["id"], "retryable", node_id=node_id, detail=f"timeout log={log_path}")
            results.append({"job_id": job["id"], "status": "retryable", "node_id": node_id})
        except Exception as exc:
            record_event(conn, job["id"], "execution-error", node_id=node_id, detail=str(exc))
            update_job_status(conn, job["id"], "retryable", node_id=node_id, detail=str(exc))
            results.append({"job_id": job["id"], "status": "retryable", "node_id": node_id})
    return results
