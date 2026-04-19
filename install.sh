#!/usr/bin/env sh
# nova-os universal installer — Linux, macOS, Termux
set -eu

REPO_URL="https://github.com/sxrubyo/nova-os.git"
DEFAULT_CLONE_DIR="$HOME/nova-os"
NOVA_DIR="$HOME/.nova"
LOCAL_BIN_DIR="$HOME/.local/bin"
BOOTSTRAP_PATH=""

is_termux() {
  [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]
}

is_macos() {
  [ "$(uname)" = "Darwin" ]
}

log() {
  printf '\033[0;32m✓ %s\033[0m\n' "$1"
}

warn() {
  printf '\033[0;33m⚠ %s\033[0m\n' "$1"
}

die() {
  printf '\033[0;31m✗ %s\033[0m\n' "$1" >&2
  exit 1
}

sudo_cmd() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    "$@"
  fi
}

detect_python() {
  for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      printf '%s' "$cmd"
      return 0
    fi
  done
  return 1
}

install_deps() {
  if is_termux; then
    log "Termux detectado"
    pkg update -y -q || true
    pkg install -y python git openssl libsqlite curl >/dev/null 2>&1 || true
    return
  fi

  if is_macos; then
    log "macOS detectado"
    if ! command -v brew >/dev/null 2>&1; then
      warn "Homebrew no está instalado; se omite instalación automática de dependencias"
      return
    fi
    brew install python git curl >/dev/null 2>&1 || true
    return
  fi

  log "Linux detectado"
  if command -v apt-get >/dev/null 2>&1; then
    sudo_cmd apt-get update -qq
    sudo_cmd apt-get install -y -qq python3 python3-pip python3-venv git curl sqlite3
  elif command -v dnf >/dev/null 2>&1; then
    sudo_cmd dnf install -y python3 python3-pip python3-virtualenv git curl sqlite
  elif command -v pacman >/dev/null 2>&1; then
    sudo_cmd pacman -Sy --noconfirm python python-pip git curl sqlite
  else
    warn "No se detectó gestor de paquetes soportado; continúo con las dependencias existentes"
  fi
}

setup_repo() {
  if [ -f "./nova.py" ] && [ -d "./nova" ] && [ -f "./requirements.txt" ]; then
    REPO_DIR="$(pwd)"
    log "Usando repo actual en $REPO_DIR"
    return
  fi

  if [ -d "$DEFAULT_CLONE_DIR/.git" ]; then
    log "Actualizando repo existente en $DEFAULT_CLONE_DIR"
    git -C "$DEFAULT_CLONE_DIR" pull --ff-only >/dev/null 2>&1 || git -C "$DEFAULT_CLONE_DIR" pull --no-rebase >/dev/null 2>&1 || true
    REPO_DIR="$DEFAULT_CLONE_DIR"
    return
  fi

  log "Clonando nova-os en $DEFAULT_CLONE_DIR"
  git clone "$REPO_URL" "$DEFAULT_CLONE_DIR" >/dev/null 2>&1 || die "No se pudo clonar $REPO_URL"
  REPO_DIR="$DEFAULT_CLONE_DIR"
}

resolve_bootstrap() {
  BOOTSTRAP_PATH="$REPO_DIR/nova/bootstrap.py"
  [ -f "$BOOTSTRAP_PATH" ] || die "No se encontró $BOOTSTRAP_PATH"
}

install_runtime() {
  PYTHON_BIN="$(detect_python)" || die "Python no está disponible"
  "$PYTHON_BIN" "$BOOTSTRAP_PATH" install \
    --repo "$REPO_DIR" \
    --bin-dir "$LOCAL_BIN_DIR" \
    --home-dir "$HOME" \
    --python-bin "$PYTHON_BIN" >/dev/null 2>&1 || die "No se pudo bootstrapear el runtime aislado"
  export PATH="$LOCAL_BIN_DIR:$PATH"
  log "CLI y runtime aislado instalados"
}

start_nova() {
  mkdir -p "$NOVA_DIR"
  LOG_FILE="$NOVA_DIR/nova.log"
  PID_FILE="$NOVA_DIR/nova.pid"
  NOVA_CMD="$LOCAL_BIN_DIR/nova"

  if is_termux; then
    log "Iniciando Nova en modo headless Termux"
    nohup "$NOVA_CMD" serve --host 0.0.0.0 --port 8000 --api-only >"$LOG_FILE" 2>&1 &
    echo "$!" > "$PID_FILE"
    log "Nova disponible en http://127.0.0.1:8000"
    return
  fi

  if command -v pm2 >/dev/null 2>&1; then
    pm2 delete nova-os >/dev/null 2>&1 || true
    pm2 start "$NOVA_CMD" --name nova-os --interpreter sh -- serve --host 0.0.0.0 --port 8000 --api-only >/dev/null 2>&1 || die "pm2 no pudo iniciar Nova"
    log "Nova iniciada con PM2"
    return
  fi

  if command -v systemctl >/dev/null 2>&1 && { [ "$(id -u)" -eq 0 ] || command -v sudo >/dev/null 2>&1; }; then
    SERVICE_FILE="/etc/systemd/system/nova-os.service"
    sudo_cmd sh -c "cat > '$SERVICE_FILE' <<EOF
[Unit]
Description=Nova OS Governance Layer
After=network.target

[Service]
Type=simple
User=$(id -un)
WorkingDirectory=$REPO_DIR
ExecStart=$NOVA_CMD serve --host 0.0.0.0 --port 8000 --api-only
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF"
    sudo_cmd systemctl daemon-reload
    sudo_cmd systemctl enable --now nova-os >/dev/null 2>&1 || die "systemd no pudo iniciar Nova"
    log "Nova iniciada con systemd"
    return
  fi

  nohup "$NOVA_CMD" serve --host 0.0.0.0 --port 8000 --api-only >"$LOG_FILE" 2>&1 &
  echo "$!" > "$PID_FILE"
  log "Nova iniciada con nohup"
}

main() {
  install_deps
  setup_repo
  resolve_bootstrap
  install_runtime
  start_nova
  log "Instalación completada"
  printf '\nComandos útiles:\n'
  printf '  nova --help\n'
  printf '  tail -f %s/nova.log\n' "$NOVA_DIR"
}

main "$@"
