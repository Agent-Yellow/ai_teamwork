# Implementation Plan: Autonomous AI Agent System (v1.2 Spec)

Based on the interview with Nat Eliason about his autonomous AI agent (Felix) and three rounds of critical security, control, and state management feedback, here is the exact production-ready v1.2 control plane spec.

## 1. Core Architecture: The Control Plane

### The MacBook Air M1 (8GB) - Available 24/7
- **Role:** The "Control Plane". It acts as the scheduler, message ingress, state manager, and job supervisor.

*Division of Labor:*
- **The Control Plane (Local Machine & Scripts):** Handles orchestration, job scheduling (cron/heartbeat), managing explicit job state (`jobs/active.json`), fetching logs, routing messages from Telegram, and executing the CLI commands.
- **The Language Model (ChatGPT/Gemini API):** Handles pure reasoning, code generation, parsing errors, drafting copy, and deciding *which* predefined tool to call next based on the state provided by the Control Plane.

## 2. Integrated Skills & CLIs (Strictly Scoped)
To prevent building a sprawling attack surface, v1.2 limits integrations purely to core development tooling.
- **GitHub:** Full `gh` CLI access for pushing code and managing PRs.
- **Vercel:** Vercel CLI for automated deployments.
- **Stripe:** Stripe API keys, rigidly locked to **Test Mode**.
- **Messaging:** Telegram group chat exclusively.

## 3. Policy & State: The Memory Model
Memory is treated strictly as policy + state, divided precisely:

1. **`daily_notes/` (What happened):** Current-state logs, API calls made, and tasks started today.
2. **`projects/` (Facts & Product State):** Specs, PRDs, checklists, launch docs, and status summaries. *(Code lives purely in Git repositories).*
3. **`tacit_knowledge/` (Source of Truth for Rules):** A folder storing structured source documents on security, preferences, and operational guidelines.
4. **`MEMORY.md` (Distilled Runtime Policy):** A small, compiled, always-loaded policy file generated from `tacit_knowledge/`. It contains *only* hard constraints, trusted channels, approval rules, and core operating preferences.

## 4. Automation Pipelines & Job State

### Explicit Job Registry
Jobs are no longer vaguely tracked. The heartbeat relies on a deterministic state machine:
- `jobs/active.json` tracks exactly what is `queued`, `running`, `failed`, `retryable`, or `awaiting_approval`.

### The Narrow Heartbeat (Minutely/Hourly)
A supervisor cron job that:
- Reads `jobs/active.json` to check active job/deployment statuses.
- Restarts safe/idempotent `retryable` jobs.
- Notifies the user on completion, blockage, or if explicit approval is needed.

### Nightly Consolidation (2:00 AM)
A separate scheduled process that rolls daily notes forward, extracts durable lessons into `tacit_knowledge/`, re-compiles the `MEMORY.md` policy, updates project statuses, and carries forward unfinished jobs.

## 5. Operational Boundaries & Observability

### Explicit Approval Boundaries (Negative Constraints)
The agent *cannot*:
- Make live billing changes or use Stripe live-mode without explicit `@jothk` approval.
- Make DNS changes or purchase new domains without explicit approval.
- Rotate secrets or delete critical project files without explicit approval.
- Publish public content without approval.

**Secret-Handling Rule:** Secrets (API keys, tokens) are NEVER written into notes, logs, PRDs, or approval files. All logs must aggressively redact sensitive `.env` values before writing to disk.

### Allowed Autonomous Actions (Positive Constraints)
The agent *is authorized* to autonomously:
- Generate PRDs, support docs, and landing page copy.
- Scaffold code repositories and push to branch.
- Deploy preview links to Vercel.
- Create Stripe test products/prices.
- Run safe/idempotent retry loops for failed scripts.

### The Approval Handoff Format
When the agent pauses for human authorization (`awaiting_approval` state), it must populate `logs/approvals_needed.md` using this strict template:
- **Action requested:** 
- **Reason:** 
- **Exact command or change proposed:** 
- **Rollback path:** 
- **Deadline/urgency:** 
- **Affected systems:** 

### Logs and Auditability
- `logs/actions.log` (Every command executed)
- `logs/errors.log` (Stack traces and API failures)
- `logs/approvals_needed.md` (Queue of actions waiting for sign-off)
- `logs/daily_summary.md` (Generated nightly)

### The Hard Kill Switch ("Safe Mode")
A single `emergency_stop.sh` script is available to immediately:
- Disable the Heartbeat cron.
- Terminate any running job execution scripts.
- Freeze `jobs/active.json`.
- Allow read-only status reporting over Telegram.
- *State and logs are fully preserved for debugging.*

## 6. Product Selection Default (The Target)
**Default v1.2 Target:** A **Paid Template/Toolkit**.
*Definition of "Done" for the toolkit loop:*
- Landing page live on a Vercel preview URL.
- Stripe test checkout link working and verified.
- Delivery asset generated (PDF/Zip) and hosted.
- Support FAQ drafted.
- Launch checklist complete.
- Final approval packet formatted and sent to the user on Telegram.
