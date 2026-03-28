from __future__ import annotations

import json
import os
import socket
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_JOB_SNAPSHOT = {
    "queued": [],
    "running": [],
    "failed": [],
    "retryable": [],
    "awaiting_approval": [],
    "assigned": [],
    "completed": [],
}

ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def repo_root() -> Path:
    raw = os.environ.get("AI_OPERATOR_ROOT")
    if not raw:
        return ROOT
    return Path(raw).expanduser().resolve()


def ensure_runtime_dirs(root: Path | None = None) -> dict[str, Path]:
    root = root or repo_root()
    paths = {
        "logs": root / "logs",
        "job_logs": root / "logs" / "jobs",
        "state": root / "state",
        "daily_notes": root / "live" / "daily_notes",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def config_path(root: Path | None = None) -> Path:
    root = root or repo_root()
    override = os.environ.get("AI_OPERATOR_CONFIG")
    if override:
        return Path(override).expanduser().resolve()
    preferred = root / "control_plane" / "config.json"
    if preferred.exists():
        return preferred
    return root / "control_plane" / "config.example.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_config() -> dict[str, Any]:
    hostname = socket.gethostname().lower()
    return {
        "dispatcher": {
            "database_path": "state/control_plane.db",
            "lease_seconds": 900,
            "stale_after_seconds": 900,
            "execution_timeout_seconds": 1800,
            "probe_timeout_seconds": 15,
        },
        "openclaw": {
            "gateway_host": hostname,
            "gateway_url": "http://127.0.0.1:18789",
            "transport": "local",
            "topology": "single-host",
        },
        "local_node": {
            "id": hostname,
            "display_name": hostname,
            "role": "worker",
            "transport": "local",
            "address": "127.0.0.1",
            "capabilities": ["shell"],
            "heartbeat_ttl_seconds": 900,
        },
        "nodes": [],
    }


def load_config(root: Path | None = None) -> dict[str, Any]:
    root = root or repo_root()
    config = default_config()
    path = config_path(root)
    if path.exists():
        with open(path, "r", encoding="utf-8") as handle:
            config = _deep_merge(config, json.load(handle))
    return config


def db_path(root: Path | None = None, config: dict[str, Any] | None = None) -> Path:
    root = root or repo_root()
    config = config or load_config(root)
    raw = config.get("dispatcher", {}).get("database_path", "state/control_plane.db")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def connect_db(root: Path | None = None, config: dict[str, Any] | None = None) -> sqlite3.Connection:
    root = root or repo_root()
    ensure_runtime_dirs(root)
    config = config or load_config(root)
    path = db_path(root, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL,
            transport TEXT NOT NULL,
            address TEXT,
            capabilities_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'offline',
            notes TEXT,
            last_seen TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            assigned_node TEXT,
            command TEXT,
            approval_required INTEGER NOT NULL DEFAULT 0,
            required_capabilities_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            lease_expires_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS job_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            node_id TEXT,
            event_type TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    node_columns = {row["name"] for row in conn.execute("PRAGMA table_info(nodes)").fetchall()}
    if "metadata_json" not in node_columns:
        conn.execute("ALTER TABLE nodes ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
    job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "metadata_json" not in job_columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
    conn.commit()
    return conn


def normalize_capabilities(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return sorted({item.strip() for item in value.split(",") if item.strip()})
    if isinstance(value, list):
        return sorted({str(item).strip() for item in value if str(item).strip()})
    return []


def seed_nodes(conn: sqlite3.Connection, config: dict[str, Any]) -> None:
    now = iso_now()
    nodes = list(config.get("nodes", []))
    local_id = config.get("local_node", {}).get("id")
    if local_id and not any(node.get("id") == local_id for node in nodes):
        nodes.append(config["local_node"])
    for node in nodes:
        conn.execute(
            """
            INSERT INTO nodes (
                id, display_name, role, transport, address, capabilities_json,
                metadata_json, status, notes, last_seen, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'offline', ?, NULL, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role,
                transport = excluded.transport,
                address = excluded.address,
                capabilities_json = excluded.capabilities_json,
                metadata_json = excluded.metadata_json,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                node["id"],
                node.get("display_name", node["id"]),
                node.get("role", "worker"),
                node.get("transport", "tailscale"),
                node.get("address", ""),
                json.dumps(normalize_capabilities(node.get("capabilities")), sort_keys=True),
                json.dumps(node.get("metadata", {}), sort_keys=True),
                node.get("notes"),
                now,
                now,
            ),
        )
    conn.commit()


def local_node_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("local_node", default_config()["local_node"])


def check_in_node(
    conn: sqlite3.Connection,
    node_id: str,
    *,
    display_name: str,
    role: str,
    transport: str,
    address: str,
    capabilities: list[str],
    metadata: dict[str, Any] | None = None,
    notes: str | None = None,
    status: str = "online",
) -> None:
    now = iso_now()
    conn.execute(
        """
        INSERT INTO nodes (
            id, display_name, role, transport, address, capabilities_json,
            metadata_json, status, notes, last_seen, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            display_name = excluded.display_name,
            role = excluded.role,
            transport = excluded.transport,
            address = excluded.address,
            capabilities_json = excluded.capabilities_json,
            metadata_json = excluded.metadata_json,
            status = excluded.status,
            notes = excluded.notes,
            last_seen = excluded.last_seen,
            updated_at = excluded.updated_at
        """,
        (
            node_id,
            display_name,
            role,
            transport,
            address,
            json.dumps(normalize_capabilities(capabilities), sort_keys=True),
            json.dumps(metadata or {}, sort_keys=True),
            status,
            notes,
            now,
            now,
            now,
        ),
    )
    conn.commit()


def mark_stale_nodes(conn: sqlite3.Connection, stale_after_seconds: int) -> int:
    cutoff = utc_now() - timedelta(seconds=stale_after_seconds)
    changed = 0
    rows = conn.execute("SELECT id, last_seen, status FROM nodes").fetchall()
    for row in rows:
        last_seen = parse_ts(row["last_seen"])
        if row["status"] == "online" and last_seen and last_seen < cutoff:
            conn.execute(
                "UPDATE nodes SET status = 'offline', updated_at = ? WHERE id = ?",
                (iso_now(), row["id"]),
            )
            changed += 1
    conn.commit()
    return changed


def record_event(
    conn: sqlite3.Connection,
    job_id: str,
    event_type: str,
    *,
    node_id: str | None = None,
    detail: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO job_events (job_id, node_id, event_type, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (job_id, node_id, event_type, detail, iso_now()),
    )
    conn.commit()


def enqueue_job(
    conn: sqlite3.Connection,
    *,
    name: str,
    command: str,
    required_capabilities: list[str],
    metadata: dict[str, Any] | None = None,
    approval_required: bool = False,
) -> str:
    job_id = str(uuid.uuid4())
    now = iso_now()
    conn.execute(
        """
        INSERT INTO jobs (
            id, name, status, assigned_node, command, approval_required,
            required_capabilities_json, metadata_json, lease_expires_at,
            created_at, updated_at
        ) VALUES (?, ?, 'queued', NULL, ?, ?, ?, ?, NULL, ?, ?)
        """,
        (
            job_id,
            name,
            command,
            int(approval_required),
            json.dumps(normalize_capabilities(required_capabilities), sort_keys=True),
            json.dumps(metadata or {}, sort_keys=True),
            now,
            now,
        ),
    )
    conn.commit()
    record_event(conn, job_id, "queued", detail=command)
    return job_id


def update_job_status(
    conn: sqlite3.Connection,
    job_id: str,
    status: str,
    *,
    node_id: str | None = None,
    detail: str | None = None,
) -> None:
    conn.execute(
        """
        UPDATE jobs
        SET status = ?, updated_at = ?, assigned_node = COALESCE(?, assigned_node)
        WHERE id = ?
        """,
        (status, iso_now(), node_id, job_id),
    )
    conn.commit()
    record_event(conn, job_id, f"status:{status}", node_id=node_id, detail=detail)


def import_legacy_jobs(conn: sqlite3.Connection, root: Path | None = None) -> int:
    root = root or repo_root()
    path = root / "jobs" / "active.json"
    if not path.exists():
        return 0
    existing = conn.execute("SELECT COUNT(*) AS count FROM jobs").fetchone()["count"]
    if existing:
        return 0
    with open(path, "r", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    imported = 0
    for status, items in snapshot.items():
        if not isinstance(items, list):
            continue
        for item in items:
            now = iso_now()
            name = item.get("name", "Legacy job")
            command = item.get("command", "")
            required = normalize_capabilities(item.get("required_capabilities"))
            metadata = {k: v for k, v in item.items() if k not in {"name", "command", "required_capabilities"}}
            job_id = item.get("id", str(uuid.uuid4()))
            conn.execute(
                """
                INSERT INTO jobs (
                    id, name, status, assigned_node, command, approval_required,
                    required_capabilities_json, metadata_json, lease_expires_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    job_id,
                    name,
                    status,
                    command,
                    int(bool(item.get("approval_required"))),
                    json.dumps(required, sort_keys=True),
                    json.dumps(metadata, sort_keys=True),
                    now,
                    now,
                ),
            )
            imported += 1
    conn.commit()
    return imported


def fetch_jobs(conn: sqlite3.Connection, *, statuses: list[str] | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM jobs"
    params: list[Any] = []
    if statuses:
        placeholders = ", ".join("?" for _ in statuses)
        query += f" WHERE status IN ({placeholders})"
        params.extend(statuses)
    query += " ORDER BY created_at ASC"
    rows = conn.execute(query, params).fetchall()
    jobs = []
    for row in rows:
        jobs.append(
            {
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "assigned_node": row["assigned_node"],
                "command": row["command"],
                "approval_required": bool(row["approval_required"]),
                "required_capabilities": json.loads(row["required_capabilities_json"]),
                "metadata": json.loads(row["metadata_json"]),
                "lease_expires_at": row["lease_expires_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return jobs


def fetch_online_nodes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM nodes WHERE status = 'online' ORDER BY role ASC, id ASC"
    ).fetchall()
    return [
        {
            "id": row["id"],
            "display_name": row["display_name"],
            "role": row["role"],
            "transport": row["transport"],
            "address": row["address"],
            "capabilities": json.loads(row["capabilities_json"]),
            "metadata": json.loads(row["metadata_json"]),
            "last_seen": row["last_seen"],
        }
        for row in rows
    ]


def fetch_nodes(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM nodes ORDER BY role ASC, id ASC").fetchall()
    return [
        {
            "id": row["id"],
            "display_name": row["display_name"],
            "role": row["role"],
            "transport": row["transport"],
            "address": row["address"],
            "capabilities": json.loads(row["capabilities_json"]),
            "metadata": json.loads(row["metadata_json"]),
            "status": row["status"],
            "notes": row["notes"],
            "last_seen": row["last_seen"],
        }
        for row in rows
    ]


def fetch_node(conn: sqlite3.Connection, node_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "role": row["role"],
        "transport": row["transport"],
        "address": row["address"],
        "capabilities": json.loads(row["capabilities_json"]),
        "metadata": json.loads(row["metadata_json"]),
        "status": row["status"],
        "notes": row["notes"],
        "last_seen": row["last_seen"],
    }


def configured_nodes(config: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = {node["id"]: dict(node) for node in config.get("nodes", [])}
    local = config.get("local_node")
    if local:
        local_copy = dict(local)
        local_copy.setdefault("transport", "local")
        nodes[local_copy["id"]] = local_copy
    return list(nodes.values())


def node_config(config: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in configured_nodes(config):
        if node["id"] == node_id:
            return node
    return None


def merge_job_metadata(
    conn: sqlite3.Connection,
    job_id: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    row = conn.execute("SELECT metadata_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
    metadata = json.loads(row["metadata_json"]) if row and row["metadata_json"] else {}
    metadata.update(values)
    conn.execute(
        "UPDATE jobs SET metadata_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(metadata, sort_keys=True), iso_now(), job_id),
    )
    conn.commit()
    return metadata


def dispatch_queued_jobs(conn: sqlite3.Connection, config: dict[str, Any]) -> list[tuple[str, str]]:
    lease_seconds = int(config.get("dispatcher", {}).get("lease_seconds", 900))
    online_nodes = fetch_online_nodes(conn)
    assignments: list[tuple[str, str]] = []
    if not online_nodes:
        return assignments

    for job in fetch_jobs(conn, statuses=["retryable"]):
        update_job_status(conn, job["id"], "queued", detail="Moved from retryable during heartbeat")

    jobs = fetch_jobs(conn, statuses=["queued"])
    for job in jobs:
        if job["approval_required"]:
            update_job_status(conn, job["id"], "awaiting_approval", detail="Approval required before dispatch")
            continue

        preferred_node = job["metadata"].get("preferred_node")
        required = set(job["required_capabilities"])
        eligible = []
        for node in online_nodes:
            caps = set(node["capabilities"])
            if required.issubset(caps):
                eligible.append(node)

        if preferred_node:
            eligible.sort(key=lambda node: (node["id"] != preferred_node, node["id"]))

        if not eligible:
            continue

        chosen = eligible[0]
        lease_expires_at = (utc_now() + timedelta(seconds=lease_seconds)).isoformat()
        conn.execute(
            """
            UPDATE jobs
            SET status = 'assigned', assigned_node = ?, lease_expires_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (chosen["id"], lease_expires_at, iso_now(), job["id"]),
        )
        conn.commit()
        record_event(
            conn,
            job["id"],
            "assigned",
            node_id=chosen["id"],
            detail=f"Dispatched to {chosen['id']}",
        )
        assignments.append((job["id"], chosen["id"]))
    return assignments


def write_legacy_snapshot(conn: sqlite3.Connection, root: Path | None = None) -> Path:
    root = root or repo_root()
    path = root / "jobs" / "active.json"
    snapshot = dict(DEFAULT_JOB_SNAPSHOT)
    for job in fetch_jobs(conn):
        if job["status"] in snapshot:
            snapshot[job["status"]].append(job)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
    return path
