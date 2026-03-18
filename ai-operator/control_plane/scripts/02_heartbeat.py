import os
import json
from datetime import datetime

def check_heartbeat():
    job_file = os.path.join(os.path.dirname(__file__), '../../jobs/active.json')
    log_file = os.path.join(os.path.dirname(__file__), '../../logs/heartbeat.log')
    approvals_md = os.path.join(os.path.dirname(__file__), '../../logs/approvals_needed.md')
    
    with open(job_file, 'r', encoding='utf-8') as f:
        jobs = json.load(f)

    timestamp = datetime.now().isoformat()
    msg = f"[{timestamp}] Heartbeat tick. "
    
    # Process Queued
    if jobs.get('queued'):
        msg += f"Found {len(jobs['queued'])} queued jobs. Attempting execution. "
        # Placeholder for executing loop
    
    # Process Awaiting Approval
    if jobs.get('awaiting_approval'):
        msg += f"Found {len(jobs['awaiting_approval'])} jobs awaiting approval. Checking logs/approvals_needed.md. "
        
        # Ensure approvals template is written
        if not os.path.exists(approvals_md) or os.path.getsize(approvals_md) == 0:
            job_name = jobs['awaiting_approval'][0].get("name", "Unknown Job")
            with open(approvals_md, 'w', encoding='utf-8') as f:
                f.write(f"## Approval Needed for {job_name}\n\n")
                f.write("- **Action requested:** \n")
                f.write("- **Reason:** \n")
                f.write("- **Exact command or change proposed:** \n")
                f.write("- **Rollback path:** \n")
                f.write("- **Deadline/urgency:** \n")
                f.write("- **Affected systems:** \n")

    # Process Retryable
    if jobs.get('retryable'):
        msg += f"Found {len(jobs['retryable'])} retryable jobs. Moving to queued. "
        jobs['queued'].extend(jobs['retryable'])
        jobs['retryable'] = []

    # Save state
    with open(job_file, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, indent=2)

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(msg + "\n")
        
    print(msg)

if __name__ == "__main__":
    check_heartbeat()
