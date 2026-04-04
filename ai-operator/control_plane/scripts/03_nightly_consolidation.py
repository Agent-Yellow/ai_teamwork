from datetime import datetime
import subprocess
from pathlib import Path

from _script_env import setup_import_path

setup_import_path()

from control_plane.runtime import connect_db, ensure_runtime_dirs, fetch_jobs, load_config, repo_root, write_legacy_snapshot

def run_consolidation():
    root = repo_root()
    paths = ensure_runtime_dirs(root)
    config = load_config(root)
    conn = connect_db(root, config)
    daily_notes_dir = root / "live" / "daily_notes"
    nightly_log = paths["logs"] / "nightly.log"
    daily_summary_md = paths["logs"] / "daily_summary.md"

    timestamp = datetime.now().isoformat()
    msg = f"[{timestamp}] Starting Nightly Consolidation...\n"

    note_files = sorted(Path(daily_notes_dir).glob("*.md"))
    queued = len(fetch_jobs(conn, statuses=["queued"]))
    assigned = len(fetch_jobs(conn, statuses=["assigned"]))
    failed = len(fetch_jobs(conn, statuses=["failed"]))
    awaiting = len(fetch_jobs(conn, statuses=["awaiting_approval"]))

    msg += f"Summarizing daily notes in {daily_notes_dir} ({len(note_files)} files)...\n"
    with open(daily_summary_md, 'a', encoding='utf-8') as f:
        f.write(f"\n## Summary for {timestamp}\n")
        f.write(f"- Daily note files: {len(note_files)}\n")
        f.write(f"- Queued jobs: {queued}\n")
        f.write(f"- Assigned jobs: {assigned}\n")
        f.write(f"- Failed jobs: {failed}\n")
        f.write(f"- Awaiting approval: {awaiting}\n")

    # Re-run bootstrap to compile MEMORY.md if rules changed
    bootstrap_script = root / "control_plane" / "scripts" / "01_bootstrap.py"
    msg += f"Recompiling MEMORY.md runtime policy...\n"
    try:
        subprocess.run(['python3', str(bootstrap_script)], check=True, capture_output=True)
        msg += "MEMORY.md compiled successfully.\n"
    except Exception as e:
        msg += f"Error compiling MEMORY.md: {e}\n"

    snapshot_path = write_legacy_snapshot(conn, root)
    msg += f"Legacy snapshot refreshed at {snapshot_path}.\n"

    # Finalize log
    msg += "Nightly Consolidation complete.\n"

    with open(nightly_log, 'a', encoding='utf-8') as f:
        f.write(msg + "\n")
    print(msg)

if __name__ == "__main__":
    run_consolidation()
