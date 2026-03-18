#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "ai-operator"
STATE = ROOT / "control_plane/state"
LOGS = ROOT / "control_plane/logs"
LIVE = ROOT / "live"

JOBS_FILE = STATE / "jobs.json"
SYSTEM_FILE = STATE / "system.json"
LAST_HEARTBEAT_FILE = STATE / "last_heartbeat.json"
PAUSED_FILE = STATE / "PAUSED"

ACTIONS_LOG = LOGS / "actions.log"
ERRORS_LOG = LOGS / "errors.log"
APPROVALS_FILE = LIVE / "approvals_needed.md"

SAFE_AUTONOMOUS_TYPES = {
    "write_prd",
    "write_copy",
    "scaffold_repo",
    "create_vercel_preview",
    "create_stripe_test_product",
    "retry_safe_job",
    "update_status_files",
}

def now() -> str:
    return datetime.utcnow().isoformat()

def log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(f"[{now()}] {message}\n")

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())

def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))

def requires_approval(job: dict) -> bool:
    return job.get("type") not in SAFE_AUTONOMOUS_TYPES

def append_approval(job: dict) -> None:
    with APPROVALS_FILE.open("a") as f:
        f.write(
            f"\n## Request\n"
            f"- Action: {job.get('title')}\n"
            f"- Reason: Job type requires approval\n"
            f"- Exact command or change: {job.get('type')}\n"
            f"- Affected systems: {job.get('repo_path', 'n/a')}\n"
            f"- Rollback path: revert git changes / cancel deployment\n"
            f"- Urgency: normal\n"
            f"- Requested at: {now()}\n"
            f"- Status: pending\n"
        )

def process_job(job: dict) -> dict:
    status = job.get("status")
    if status in {"done", "failed", "awaiting_approval"}:
        return job

    if requires_approval(job):
        job["status"] = "awaiting_approval"
        job["updated_at"] = now()
        append_approval(job)
        log(ACTIONS_LOG, f"approval requested for {job['id']}: {job['title']}")
        return job

    if status == "queued":
        job["status"] = "running"
        job["updated_at"] = now()
        log(ACTIONS_LOG, f"started job {job['id']}: {job['title']}")
        return job

    if status == "running":
        retries = job.get("safe_retry_count", 0)
        max_retries = job.get("max_retries", 2)

        if retries < max_retries:
            job["safe_retry_count"] = retries + 1
            job["status"] = "done"
            job["updated_at"] = now()
            log(ACTIONS_LOG, f"completed job {job['id']}: {job['title']}")
        else:
            job["status"] = "failed"
            job["updated_at"] = now()
            log(ERRORS_LOG, f"failed job {job['id']}: {job['title']}")
        return job

    return job

def main() -> None:
    if PAUSED_FILE.exists():
        log(ACTIONS_LOG, "heartbeat skipped: system paused")
        return

    jobs_data = load_json(JOBS_FILE) or {"jobs": []}
    updated_jobs = []

    for job in jobs_data.get("jobs", []):
        try:
            updated_jobs.append(process_job(job))
        except Exception as e:
            log(ERRORS_LOG, f"job processing error for {job.get('id', 'unknown')}: {e}")
            job["status"] = "failed"
            job["updated_at"] = now()
            updated_jobs.append(job)

    jobs_data["jobs"] = updated_jobs
    save_json(JOBS_FILE, jobs_data)
    save_json(LAST_HEARTBEAT_FILE, {"last_run": now()})

if __name__ == "__main__":
    main()
