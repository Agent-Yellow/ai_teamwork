# AI Operator (v1.2 Control Plane Spec)

This repository contains the physical scaffolding and execution scripts for a supervised, autonomous AI operator designed to run 24/7 on a constrained device (e.g., MacBook Air M1). 

## Architecture
The system explicitly divides responsibility:
1. **The Language Model:** Evaluates system state (`active.json`, `MEMORY.md`), generates code, reasoning, and handles tool usage logic.
2. **The Control Plane (Here):** A deterministic set of Python and bash scripts that supervise the LLM's tasks, handle scheduling, handle approvals, and ensure rigid security boundaries.

## Quick Start on Mac M1
1. `cp .env.example .env` and fill in your API variables.
2. Ensure you have `python3` installed via Homebrew.
3. Review `live/tacit_knowledge/policy_rules.md`. Modify any overarching security constraints.
4. Run python `control_plane/scripts/01_bootstrap.py`. This reads your tacit knowledge and auto-compiles the system read-only `live/MEMORY.md`. 
5. The `02_heartbeat.py` script is the main job runner. Add `cron.example` to your `crontab -e` to make the system fully autonomous!

## The Kill Switch
The `emergency_stop.sh` script immediately strips your cron entries, halts process trees, and freezes active json state into a read-only state. This prevents runaway loops. Run this from your terminal immediately if behavior drifts.
