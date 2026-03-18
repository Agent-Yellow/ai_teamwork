# Agent Security and Approval Policies

1. **Billing:** Never make live billing changes or use Stripe live-mode without explicit @jothk approval.
2. **DNS:** Never make DNS changes or purchase new domains without explicit approval.
3. **Secrets:** Secrets (API keys, tokens) MUST NEVER be written into notes, logs, PRDs, or approval files. All logs must aggressively redact sensitive `.env` values before writing to disk.
4. **Publishing:** Never publish public content without approval.

**Approval Handoff Format**
When requesting human approval, use exactly this template:
- Action requested:
- Reason:
- Exact command or change proposed:
- Rollback path:
- Deadline/urgency:
- Affected systems:
