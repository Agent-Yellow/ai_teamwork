#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path.home() / "ai-operator"

DIRS = [
    "control_plane/scripts",
    "control_plane/state",
    "control_plane/logs",
    "live/compiled",
    "live/daily_notes",
    "live/projects/starter_paid_toolkit",
    "live/tacit_knowledge",
    "live/runbooks",
    "jobs/queue",
    "jobs/archive",
    "repos/starter_paid_toolkit",
]

FILES = {
    "control_plane/state/jobs.json": {"jobs": []},
    "control_plane/state/system.json": {
        "version": "v1.2",
        "mode": "active",
        "last_nightly_consolidation": None,
    },
    "control_plane/state/last_heartbeat.json": {"last_run": None},
    "control_plane/config.json": {
        "root": str(ROOT),
        "heartbeat_minutes": 15,
        "max_safe_retries": 2,
        "default_product_type": "paid_template_toolkit",
    },
    "live/approvals_needed.md": "# Approvals Needed\n",
    "live/daily_summary.md": "# Daily Summary\n",
    "live/projects/_index.md": "# Projects Index\n",
    "live/projects/starter_paid_toolkit/prd.md": "# PRD\n",
    "live/projects/starter_paid_toolkit/status.md": "# Status\n- State: not_started\n",
    "live/projects/starter_paid_toolkit/launch_checklist.md": "# Launch Checklist\n",
    "live/projects/starter_paid_toolkit/support_faq.md": "# Support FAQ\n",
    "live/projects/starter_paid_toolkit/pricing.md": "# Pricing\n",
    "live/tacit_knowledge/operator_preferences.md": "# Operator Preferences\n",
    "live/tacit_knowledge/trusted_channels.md": "# Trusted Channels\n",
    "live/tacit_knowledge/security_rules.md": "# Security Rules\n",
    "live/tacit_knowledge/decision_rules.md": "# Decision Rules\n",
    "live/tacit_knowledge/quality_bar.md": "# Quality Bar\n",
    "live/tacit_knowledge/launch_constraints.md": "# Launch Constraints\n",
    "live/tacit_knowledge/lessons_learned.md": "# Lessons Learned\n",
    "live/compiled/MEMORY.md": "# Runtime Policy\n",
    ".env.example": "TELEGRAM_BOT_TOKEN=\nTELEGRAM_CHAT_ID=\nGITHUB_TOKEN=\nVERCEL_TOKEN=\nSTRIPE_SECRET_KEY_TEST=\nSTRIPE_PUBLISHABLE_KEY_TEST=\n",
    "README.md": "# AI Operator\n",
}

def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)

    for rel in DIRS:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

    for rel, content in FILES.items():
        path = ROOT / rel
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            path.write_text(json.dumps(content, indent=2))
        else:
            path.write_text(content)

    print(f"Bootstrapped: {ROOT}")

if __name__ == "__main__":
    main()
