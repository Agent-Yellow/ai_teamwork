# Mac Primary, Linux Worker

This is the deployment layout for the hardware you described:

- **Mac:** available 24/7, dedicated to OpenClaw and operator control
- **Linux laptop:** available mostly at night, dedicated to heavier worker/model tasks when online

That availability profile means the Mac must own the control plane.

## Machine Roles

### Mac primary

- Runs the main OpenClaw gateway continuously
- Owns the dispatcher state database in `state/control_plane.db`
- Runs `02_heartbeat.py` and `03_nightly_consolidation.py`
- Hosts a baseline model path that is available during the day
- Exposes the operator UI and messaging integrations

### Linux worker

- Boots Ubuntu from the second NVMe
- Runs Tailscale
- Checks in to the dispatcher with `04_node_check_in.py`
- Claims jobs assigned to `linux-night`
- Hosts heavier local models and Linux/GPU execution

## Why this split

If the Linux laptop is only awake at night, it cannot be your OpenClaw gateway or your only local model path. If you make Linux the center of the system, daytime operation fails.

This layout keeps:

- control and orchestration alive all day
- Linux as burst capacity
- failure domains simple

## Recommended model strategy

Daytime-safe default:

- Mac local model or cloud fallback for baseline operation

Night-time burst:

- Linux local models for heavier jobs

The key rule is that the default model chain must not depend on the Linux laptop being online.

## Tailscale layout

Suggested tailnet naming:

- `mac-primary`
- `linux-night`

Suggested services:

- OpenClaw gateway on Mac, reachable over Tailscale
- Dispatcher database and scripts stay local to the Mac
- Linux worker connects inbound to the Mac over tailnet and refreshes node heartbeat

## First-pass rollout

1. Install Ubuntu 24.04 LTS on the second NVMe in the Windows laptop.
2. Install Tailscale on both Mac and Linux.
3. Put the OpenClaw gateway on the Mac.
4. Put this repo on the Mac as the dispatcher source of truth.
5. Copy this repo to Linux only if you want the Linux worker to self-report with the same scripts.
6. Configure `control_plane/config.json` with the actual tailnet IPs and node IDs.
7. Bootstrap on the Mac:

   ```bash
   export AI_OPERATOR_ROOT="$HOME/ai_teamwork/ai-operator"
   python3 control_plane/scripts/01_bootstrap.py
   ```

8. Enqueue test work from the Mac:

   ```bash
   python3 control_plane/scripts/05_enqueue_job.py \
     --name "Linux smoke test" \
     --command "uname -a" \
     --requires shell,linux \
     --preferred-node linux-night
   ```

9. Check in the Mac node:

   ```bash
   python3 control_plane/scripts/04_node_check_in.py
   ```

10. Check in the Linux node when it is online:

   ```bash
   python3 control_plane/scripts/04_node_check_in.py \
     --node-id linux-night \
     --display-name "Ubuntu worker laptop" \
     --role worker \
     --transport tailscale \
     --address 100.64.0.20 \
     --capabilities shell,linux,gpu,nightly,local-models
   ```

11. Run heartbeat on the Mac:

   ```bash
   python3 control_plane/scripts/02_heartbeat.py
   ```

12. Inspect Linux-assigned work:

   ```bash
   python3 control_plane/scripts/06_claim_jobs.py --node-id linux-night
   ```

13. Update status after execution:

   ```bash
   python3 control_plane/scripts/07_update_job.py \
     --job-id <job-id> \
     --status completed \
     --node-id linux-night \
     --message "Linux smoke test finished"
   ```

## What this does not do yet

This is still a dispatcher baseline, not a full worker runtime. It does not yet:

- execute the assigned command automatically
- stream stdout/stderr back into the database
- enforce capability-specific sandbox policies
- integrate directly with OpenClaw node APIs

Those are the next layers to build after the Mac-primary topology is stable.
