#!/usr/bin/env sh
# nova-os universal installer — Linux, macOS, Termux
set -eu

REPO_URL="https://github.com/sxrubyo/nova-os.git"
DEFAULT_CLONE_DIR="$HOME/nova-os"
NOVA_DIR="$HOME/.nova"
BOOTSTRAP_PATH=""
NOVA_CMD=""

print_banner() {
  printf '\033[0;94m%s\033[0m\n' '╭──────────────────────────────────────────────────────────────╮'
  printf '\033[0;94m%s\033[0m\n' '│  .      *        .       NOVA OS // launch vector          │'
  printf '\033[0;94m%s\033[0m\n' '│     adaptive runtime bootstrap for governed operators      │'
  printf '\033[0;94m%s\033[0m\n' '│  repos • terminals • toolchains • policy • live agents     │'
  printf '\033[0;94m%s\033[0m\n' '╰──────────────────────────────────────────────────────────────╯'
}

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
  elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    sudo -n "$@"
  else
    return 1
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
    log "Termux detected"
    pkg update -y -q || true
    missing=""
    command -v python >/dev/null 2>&1 || missing="$missing python"
    command -v git >/dev/null 2>&1 || missing="$missing git"
    command -v curl >/dev/null 2>&1 || missing="$missing curl"
    command -v openssl >/dev/null 2>&1 || missing="$missing openssl"
    command -v sqlite3 >/dev/null 2>&1 || missing="$missing libsqlite"
    if [ -n "$missing" ]; then
      # shellcheck disable=SC2086
      pkg install -y $missing >/dev/null 2>&1 || true
    else
      log "Host essentials already present"
    fi
    return
  fi

  if is_macos; then
    log "macOS detected"
    if ! command -v brew >/dev/null 2>&1; then
      warn "Homebrew is not installed; skipping automatic dependency installation"
      return
    fi
    missing=""
    command -v python3 >/dev/null 2>&1 || missing="$missing python"
    command -v git >/dev/null 2>&1 || missing="$missing git"
    command -v curl >/dev/null 2>&1 || missing="$missing curl"
    if [ -n "$missing" ]; then
      # shellcheck disable=SC2086
      brew install $missing >/dev/null 2>&1 || true
    else
      log "Host essentials already present"
    fi
    return
  fi

  log "Linux detected"
  if [ "$(id -u)" -ne 0 ] && ! { command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; }; then
    warn "No non-interactive sudo available; continuing with existing dependencies"
    return
  fi
  if command -v apt-get >/dev/null 2>&1; then
    missing=""
    command -v git >/dev/null 2>&1 || missing="$missing git"
    command -v curl >/dev/null 2>&1 || missing="$missing curl"
    command -v sqlite3 >/dev/null 2>&1 || missing="$missing sqlite3"
    if ! command -v python3 >/dev/null 2>&1; then
      missing="$missing python3 python3-pip python3-venv"
    else
      python3 -c "import venv" >/dev/null 2>&1 || missing="$missing python3-venv"
      python3 -m pip --version >/dev/null 2>&1 || missing="$missing python3-pip"
    fi
    [ -n "$missing" ] || {
      log "Host essentials already present"
      return
    }
    sudo_cmd apt-get update -qq
    # shellcheck disable=SC2086
    sudo_cmd apt-get install -y -qq $missing
  elif command -v dnf >/dev/null 2>&1; then
    missing=""
    command -v git >/dev/null 2>&1 || missing="$missing git"
    command -v curl >/dev/null 2>&1 || missing="$missing curl"
    command -v sqlite3 >/dev/null 2>&1 || missing="$missing sqlite"
    if ! command -v python3 >/dev/null 2>&1; then
      missing="$missing python3 python3-pip python3-virtualenv"
    else
      python3 -c "import venv" >/dev/null 2>&1 || missing="$missing python3-virtualenv"
      python3 -m pip --version >/dev/null 2>&1 || missing="$missing python3-pip"
    fi
    [ -n "$missing" ] || {
      log "Host essentials already present"
      return
    }
    # shellcheck disable=SC2086
    sudo_cmd dnf install -y $missing
  elif command -v pacman >/dev/null 2>&1; then
    missing=""
    command -v git >/dev/null 2>&1 || missing="$missing git"
    command -v curl >/dev/null 2>&1 || missing="$missing curl"
    command -v sqlite3 >/dev/null 2>&1 || missing="$missing sqlite"
    if ! command -v python >/dev/null 2>&1; then
      missing="$missing python python-pip"
    else
      python -m pip --version >/dev/null 2>&1 || missing="$missing python-pip"
    fi
    [ -n "$missing" ] || {
      log "Host essentials already present"
      return
    }
    # shellcheck disable=SC2086
    sudo_cmd pacman -Sy --noconfirm $missing
  else
    warn "No supported package manager detected; continuing with existing dependencies"
  fi
}

setup_repo() {
  if [ -f "./nova.py" ] && [ -d "./nova" ] && [ -f "./requirements.txt" ]; then
    REPO_DIR="$(pwd)"
    log "Using current repository at $REPO_DIR"
    return
  fi

  if [ -d "$DEFAULT_CLONE_DIR/.git" ]; then
    log "Updating existing repository in $DEFAULT_CLONE_DIR"
    git -C "$DEFAULT_CLONE_DIR" pull --ff-only >/dev/null 2>&1 || git -C "$DEFAULT_CLONE_DIR" pull --no-rebase >/dev/null 2>&1 || true
    REPO_DIR="$DEFAULT_CLONE_DIR"
    return
  fi

  log "Cloning nova-os into $DEFAULT_CLONE_DIR"
  git clone "$REPO_URL" "$DEFAULT_CLONE_DIR" >/dev/null 2>&1 || die "Failed to clone $REPO_URL"
  REPO_DIR="$DEFAULT_CLONE_DIR"
}

resolve_bootstrap() {
  BOOTSTRAP_PATH="$REPO_DIR/nova/bootstrap.py"
  [ -f "$BOOTSTRAP_PATH" ] || die "Could not find $BOOTSTRAP_PATH"
}

install_runtime() {
  PYTHON_BIN="$(detect_python)" || die "Python is not available"
  log "Bootstrapping isolated runtime"
  NOVA_BOOTSTRAP_EMBEDDED=1 "$PYTHON_BIN" "$BOOTSTRAP_PATH" install \
    --repo "$REPO_DIR" \
    --home-dir "$HOME" \
    --python-bin "$PYTHON_BIN" || die "Failed to bootstrap the isolated runtime"
  NOVA_CMD="$("$PYTHON_BIN" - <<PY
import sys
sys.path.insert(0, "$REPO_DIR")
from nova.bootstrap import select_bin_dir
print(select_bin_dir(home_dir="$HOME"))
PY
)/nova"
  [ -x "$NOVA_CMD" ] || die "Failed to resolve the installed nova wrapper"
  log "CLI and isolated runtime installed"
}

start_nova() {
  mkdir -p "$NOVA_DIR"
  LOG_FILE="$NOVA_DIR/nova.log"
  PID_FILE="$NOVA_DIR/nova.pid"

  if is_termux; then
    log "Starting Nova in Termux headless mode"
    nohup "$NOVA_CMD" serve --host 0.0.0.0 --port 8000 >"$LOG_FILE" 2>&1 &
    echo "$!" > "$PID_FILE"
    log "Nova available at http://127.0.0.1:8000"
    return
  fi

  if command -v pm2 >/dev/null 2>&1; then
    pm2 delete nova-os >/dev/null 2>&1 || true
    pm2 start "$NOVA_CMD" --name nova-os --interpreter sh -- serve --host 0.0.0.0 --port 8000 >/dev/null 2>&1 || die "PM2 failed to start Nova"
    log "Nova started with PM2"
    return
  fi

  if command -v systemctl >/dev/null 2>&1 && { [ "$(id -u)" -eq 0 ] || command -v sudo >/dev/null 2>&1; }; then
    SERVICE_FILE="/etc/systemd/system/nova-os.service"
    sudo_cmd sh -c "cat > '$SERVICE_FILE' <<EOF
[Unit]
Description=Nova OS
After=network.target

[Service]
Type=simple
User=$(id -un)
WorkingDirectory=$REPO_DIR
ExecStart=$NOVA_CMD serve --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF"
    sudo_cmd systemctl daemon-reload
    sudo_cmd systemctl enable --now nova-os >/dev/null 2>&1 || die "systemd failed to start Nova"
    log "Nova started with systemd"
    return
  fi

  nohup "$NOVA_CMD" serve --host 0.0.0.0 --port 8000 >"$LOG_FILE" 2>&1 &
  echo "$!" > "$PID_FILE"
  log "Nova started with nohup"
}

main() {
  print_banner
  install_deps
  setup_repo
  resolve_bootstrap
  install_runtime
  start_nova
  log "Installation complete"
  printf '\nUseful commands:\n'
  printf '  nova\n'
  printf '  nova help\n'
  printf '  tail -f %s/nova.log\n' "$NOVA_DIR"
}

main "$@"
