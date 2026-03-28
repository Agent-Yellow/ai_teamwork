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
- Exposes SSH so the Mac can probe and execute remote commands
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
- Linux worker exposes SSH and optional model services over the tailnet

## First-pass rollout

1. Install Ubuntu 24.04 LTS on the second NVMe in the Windows laptop.
2. Install Tailscale on both Mac and Linux.
3. Put the OpenClaw gateway on the Mac.
4. Put this repo on the Mac as the dispatcher source of truth.
5. Configure `control_plane/config.json` with the actual tailnet IPs, SSH target, and node IDs.
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

9. Run heartbeat on the Mac so it probes configured nodes:

   ```bash
   python3 control_plane/scripts/02_heartbeat.py
   ```

10. Execute assigned jobs from the Mac:

   ```bash
   python3 control_plane/scripts/08_run_assigned_jobs.py
   ```

11. Inspect Linux-assigned work:

   ```bash
   python3 control_plane/scripts/06_claim_jobs.py --node-id linux-night
   ```

12. Read execution logs:

   ```bash
   ls logs/jobs
   ```

## What this does not do yet

This is still a small Mac-led dispatcher, not a full distributed scheduler. It does not yet:

- parallelize jobs across multiple remote workers with concurrency controls
- enforce capability-specific sandbox policies
- integrate directly with OpenClaw node APIs
- manage remote model runtimes for you

Those are the next layers to build after the Mac-primary topology is stable.
