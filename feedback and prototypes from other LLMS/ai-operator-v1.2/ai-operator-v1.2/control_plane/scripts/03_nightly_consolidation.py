#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "ai-operator"
LIVE = ROOT / "live"
STATE = ROOT / "control_plane/state"
LOGS = ROOT / "control_plane/logs"

SYSTEM_FILE = STATE / "system.json"
ACTIONS_LOG = LOGS / "actions.log"
DAILY_SUMMARY = LIVE / "daily_summary.md"
COMPILED_MEMORY = LIVE / "compiled/MEMORY.md"
TACIT = LIVE / "tacit_knowledge"
DAILY_NOTES = LIVE / "daily_notes"

TACTIC_FILES = [
    "operator_preferences.md",
    "trusted_channels.md",
    "security_rules.md",
    "decision_rules.md",
    "quality_bar.md",
    "launch_constraints.md",
    "lessons_learned.md",
]

def now() -> str:
    return datetime.utcnow().isoformat()

def log(message: str) -> None:
    with ACTIONS_LOG.open("a") as f:
        f.write(f"[{now()}] {message}\n")

def compile_memory() -> None:
    parts = ["# Runtime Policy\n", f"_Compiled at {now()}_\n"]

    for name in TACTIC_FILES:
        path = TACIT / name
        if path.exists():
            parts.append(path.read_text().strip() + "\n")

    COMPILED_MEMORY.write_text("\n".join(parts))

def summarize_today() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    note_file = DAILY_NOTES / f"{today}.md"

    if note_file.exists():
        content = note_file.read_text().strip()
    else:
        content = "No daily note found."

    DAILY_SUMMARY.write_text(
        f"# Daily Summary\n\n"
        f"- Date: {today}\n"
        f"- Consolidated at: {now()}\n\n"
        f"## Source\n\n{content}\n"
    )

def update_system_state() -> None:
    data = {"version": "v1.2", "mode": "active", "last_nightly_consolidation": now()}
    SYSTEM_FILE.write_text(json.dumps(data, indent=2))

def main() -> None:
    summarize_today()
    compile_memory()
    update_system_state()
    log("nightly consolidation completed")

if __name__ == "__main__":
    main()
