# Linux Worker Bootstrap

Use [bootstrap_linux_worker.sh](bootstrap_linux_worker.sh) on the Ubuntu laptop after the NVMe is installed internally.

## What it does

- installs base packages
- enables `ssh`
- installs and enables `tailscaled`
- optionally installs `ollama`
- prepares a shared workspace directory

## Example

```bash
export TAILSCALE_HOSTNAME=linux-night
export WORKER_USER=jit9b
export WORKSPACE_DIR=/srv/ai-teamwork
export INSTALL_OLLAMA=1

bash ./ai-operator/deploy/linux/bootstrap_linux_worker.sh
```

If you already have a reusable Tailscale auth key, set `TAILSCALE_AUTH_KEY` before running the script. Otherwise it will stop after installation and print the manual `tailscale up` command.
