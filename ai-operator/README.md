# AI Operator (v1.3 Dispatcher Baseline)

This repository now includes a portable control-plane baseline for a two-machine OpenClaw setup:

- **Mac primary:** always-on gateway, scheduler, durable state owner
- **Linux worker:** optional node that checks in when online and takes Linux/GPU/local-model work

The implementation is still intentionally small, but it now boots from a fresh checkout, creates its runtime directories, persists dispatcher state in SQLite, and exposes a minimal node/job workflow instead of placeholder-only cron scripts.

## Architecture

The system explicitly divides responsibility:

1. **OpenClaw Gateway:** runs continuously on the always-on Mac and owns the operator-facing control plane.
2. **The Dispatcher (this repo):** tracks nodes, jobs, approvals, and queue snapshots with deterministic local scripts.
3. **Workers / Nodes:** check in over time, advertise capabilities, claim assigned work, and report job status transitions back to the dispatcher.

This is the intended role split for a Mac that is available 24/7 and a Linux laptop that is only online at night.

## Runtime Layout

`01_bootstrap.py` now creates and maintains the runtime paths the older repo assumed already existed:

- `logs/`
- `state/`
- `live/daily_notes/`
- `live/MEMORY.md`
- `state/control_plane.db`

The old `jobs/active.json` file is still produced as a compatibility snapshot, but SQLite is now the source of truth for nodes and jobs.

## Quick Start

1. `cd ai-operator`
2. `cp .env.example .env`
3. `cp control_plane/config.example.json control_plane/config.json`
4. Edit `control_plane/config.json` for your real tailnet IPs, node ids, and OpenClaw gateway URL.
5. Review `live/tacit_knowledge/*.md`.
6. Run:

   ```bash
   export AI_OPERATOR_ROOT="$PWD"
   python3 control_plane/scripts/01_bootstrap.py
   python3 control_plane/scripts/04_node_check_in.py
   python3 control_plane/scripts/02_heartbeat.py
   ```

## Core Scripts

- `01_bootstrap.py`: creates runtime directories, initializes SQLite, seeds node inventory, compiles `MEMORY.md`
- `02_heartbeat.py`: marks stale nodes offline, dispatches queued jobs to eligible online nodes, writes approval packet and legacy snapshot
- `03_nightly_consolidation.py`: rolls up daily counts, rebuilds `MEMORY.md`, refreshes snapshot
- `04_node_check_in.py`: refreshes a node heartbeat and capability inventory
- `05_enqueue_job.py`: adds a job to the dispatcher queue
- `06_claim_jobs.py`: lists jobs assigned to a node
- `07_update_job.py`: records worker-side job status transitions

## OpenClaw Topology

This repo is aligned to the following deployment:

- **Mac primary**
  - runs OpenClaw gateway
  - runs this dispatcher heartbeat
  - stays reachable over Tailscale
  - provides daytime-safe baseline execution and model access
- **Linux worker**
  - runs Ubuntu on the second NVMe
  - checks in when online
  - handles Linux-specific, GPU, and heavy local-model jobs
  - can disappear without taking the control plane down

See [Mac Primary Linux Worker](docs/mac_primary_linux_worker.md) for the concrete rollout plan.

## Kill Switch

`emergency_stop.sh` now respects `AI_OPERATOR_ROOT` instead of assuming a fixed install path. It removes matching cron entries, terminates script processes, and freezes the compatibility queue snapshot.
