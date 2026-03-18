# AI Operator v1.2

This package contains a lean v1.2 build sheet for a supervised autonomous product operator.

## Contents
- `control_plane/` scheduler, scripts, state, and logs
- `live/` memory, runbooks, projects, approvals, and compiled runtime policy
- `jobs/` queued and archived jobs
- `repos/` working repo roots

## Quick start
1. Copy `.env.example` to `.env` and fill in values.
2. Review and edit files in `live/tacit_knowledge/`.
3. Run `python3 control_plane/scripts/01_bootstrap.py`.
4. Add a sample job to `control_plane/state/jobs.json`.
5. Run `python3 control_plane/scripts/02_heartbeat.py`.
6. Run `python3 control_plane/scripts/03_nightly_consolidation.py`.
7. Install cron entries from `control_plane/cron.example`.
