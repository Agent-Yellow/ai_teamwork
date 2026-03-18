import os
from datetime import datetime
import subprocess

def run_consolidation():
    daily_notes_dir = os.path.join(os.path.dirname(__file__), '../../live/daily_notes')
    logs_dir = os.path.join(os.path.dirname(__file__), '../../logs')
    nightly_log = os.path.join(logs_dir, 'nightly.log')
    daily_summary_md = os.path.join(logs_dir, 'daily_summary.md')

    timestamp = datetime.now().isoformat()
    msg = f"[{timestamp}] Starting Nightly Consolidation...\n"
    
    # Placeholder: Summarize daily notes
    msg += f"Summarizing daily notes in {daily_notes_dir}...\n"
    with open(daily_summary_md, 'a', encoding='utf-8') as f:
        f.write(f"\n## Summary for {timestamp}\nNo significant events to summarize.\n")

    # Re-run bootstrap to compile MEMORY.md if rules changed
    bootstrap_script = os.path.join(os.path.dirname(__file__), '01_bootstrap.py')
    msg += f"Recompiling MEMORY.md runtime policy...\n"
    try:
        subprocess.run(['python3', bootstrap_script], check=True, capture_output=True)
        msg += "MEMORY.md compiled successfully.\n"
    except Exception as e:
        msg += f"Error compiling MEMORY.md: {e}\n"

    # Placeholder: Trim stale job state

    # Finalize log
    msg += "Nightly Consolidation complete.\n"

    with open(nightly_log, 'a', encoding='utf-8') as f:
        f.write(msg + "\n")
    print(msg)

if __name__ == "__main__":
    run_consolidation()
