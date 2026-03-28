#!/usr/bin/env bash
set -euo pipefail

WORKER_USER="${WORKER_USER:-$USER}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/srv/ai-teamwork}"
INSTALL_OLLAMA="${INSTALL_OLLAMA:-1}"
TAILSCALE_AUTH_KEY="${TAILSCALE_AUTH_KEY:-}"
TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-linux-night}"

log() {
  printf '[bootstrap] %s\n' "$1"
}

require_sudo() {
  if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required" >&2
    exit 1
  fi
}

install_base_packages() {
  log "Installing base packages"
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    git \
    jq \
    openssh-server \
    python3 \
    python3-venv \
    rsync
}

configure_ssh() {
  log "Enabling ssh service"
  sudo systemctl enable --now ssh
}

install_tailscale() {
  if command -v tailscale >/dev/null 2>&1; then
    log "Tailscale already installed"
  else
    log "Installing Tailscale"
    curl -fsSL https://tailscale.com/install.sh | sh
  fi
  sudo systemctl enable --now tailscaled
  if [[ -n "$TAILSCALE_AUTH_KEY" ]]; then
    log "Bringing Tailscale up with auth key"
    sudo tailscale up --ssh --hostname "$TAILSCALE_HOSTNAME" --auth-key "$TAILSCALE_AUTH_KEY"
  else
    log "Tailscale installed. Finish sign-in manually with: sudo tailscale up --ssh --hostname $TAILSCALE_HOSTNAME"
  fi
}

install_ollama() {
  if [[ "$INSTALL_OLLAMA" != "1" ]]; then
    log "Skipping Ollama install"
    return
  fi
  if command -v ollama >/dev/null 2>&1; then
    log "Ollama already installed"
    return
  fi
  log "Installing Ollama"
  curl -fsSL https://ollama.com/install.sh | sh
}

prepare_workspace() {
  log "Preparing workspace at $WORKSPACE_DIR"
  sudo mkdir -p "$WORKSPACE_DIR"
  sudo chown -R "$WORKER_USER":"$WORKER_USER" "$WORKSPACE_DIR"
  mkdir -p "$HOME/.ssh"
  chmod 700 "$HOME/.ssh"
}

print_next_steps() {
  cat <<EOF

Linux worker bootstrap complete.

Next steps:
  1. Verify SSH from the Mac:
     ssh ${WORKER_USER}@${TAILSCALE_HOSTNAME}
  2. Update the Mac dispatcher config if the worker hostname differs.
  3. If Ollama was installed, confirm:
     ollama list
EOF
}

main() {
  require_sudo
  install_base_packages
  configure_ssh
  install_tailscale
  install_ollama
  prepare_workspace
  print_next_steps
}

main "$@"
