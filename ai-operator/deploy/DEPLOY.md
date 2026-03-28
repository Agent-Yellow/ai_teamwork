# Service Deployment

This directory contains service templates for the two-machine layout:

- `launchd/`: Mac primary dispatcher services
- `systemd/`: Linux worker support services

## Mac primary

The Mac should run three launchd jobs:

- heartbeat every 3 minutes
- assigned-job executor every minute
- nightly consolidation at 2:00 AM

To use the templates:

1. Replace `__AI_OPERATOR_ROOT__` with the absolute path to `ai-operator`
2. Copy the plist files into `~/Library/LaunchAgents/`
3. Load them:

   ```bash
   launchctl unload ~/Library/LaunchAgents/com.agentyellow.ai-operator.heartbeat.plist 2>/dev/null || true
   launchctl unload ~/Library/LaunchAgents/com.agentyellow.ai-operator.executor.plist 2>/dev/null || true
   launchctl unload ~/Library/LaunchAgents/com.agentyellow.ai-operator.nightly.plist 2>/dev/null || true

   launchctl load ~/Library/LaunchAgents/com.agentyellow.ai-operator.heartbeat.plist
   launchctl load ~/Library/LaunchAgents/com.agentyellow.ai-operator.executor.plist
   launchctl load ~/Library/LaunchAgents/com.agentyellow.ai-operator.nightly.plist
   ```

## Linux worker

This repo no longer expects the Linux host to run the dispatcher database. The Mac probes and uses the Linux worker over SSH/Tailscale.

What the Linux host does need:

- `openssh-server`
- `tailscaled`
- a model runtime if you want local inference there

If your Ollama install does not already provide a systemd service, `systemd/ai-operator-linux-ollama.service` is a starting template.
