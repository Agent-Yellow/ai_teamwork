#!/bin/bash
# Hard Kill Switch for AI Operator v1.2

echo "Initiating AI Operator Emergency Stop..."

# 1. Remove the crontab entries to prevent heartbeat/nightly restarts
crontab -l | grep -v 'ai-operator' | crontab -
echo "Cron entries removed."

# 2. Kill any currently running execution scripts
pkill -f 'ai-operator/control_plane/scripts'
echo "Running operator processes killed."

# 3. Freeze active jobs (backup first, then clear active queues)
cp ~/ai-operator/jobs/active.json ~/ai-operator/jobs/active_frozen.json.bak
echo '{"queued": [], "running": [], "failed": [], "retryable": [], "awaiting_approval": []}' > ~/ai-operator/jobs/active.json
echo "Jobs frozen and cleared from active queue."

echo "Safe mode engaged. State and logs preserved."
