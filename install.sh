#!/usr/bin/env sh
# nova-os universal installer — Linux, macOS, Termux
set -eu

NOVA_DIR="$HOME/.nova"
REPO_ARCHIVE_URL="https://codeload.github.com/sxrubyo/nova-os/tar.gz/refs/heads/main"
REPO_DIR="$HOME/.nova/repo"
BIN_DIR="$HOME/.nova/bin"
BOOTSTRAP_PATH=""
NOVA_CMD="$BIN_DIR/nova"
TEMP_ROOT=""

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

cleanup() {
  [ -n "$TEMP_ROOT" ] && [ -d "$TEMP_ROOT" ] && rm -rf "$TEMP_ROOT"
}

trap cleanup EXIT INT TERM

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
  mkdir -p "$NOVA_DIR" "$BIN_DIR"
  TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/nova-os.XXXXXX")"
  ARCHIVE_PATH="$TEMP_ROOT/nova-os.tar.gz"

  log "Downloading Nova OS"
  curl -fsSL "$REPO_ARCHIVE_URL" -o "$ARCHIVE_PATH" || die "Failed to download $REPO_ARCHIVE_URL"
  log "Archive downloaded"

  log "Extracting Nova OS"
  tar -xzf "$ARCHIVE_PATH" -C "$TEMP_ROOT" || die "Failed to extract Nova OS archive"
  EXTRACTED_DIR="$(find "$TEMP_ROOT" -maxdepth 1 -type d -name 'nova-os-*' | head -n 1)"
  [ -n "$EXTRACTED_DIR" ] || die "Could not locate extracted Nova OS repository"
  [ -f "$EXTRACTED_DIR/nova/bootstrap.py" ] || die "Extracted archive does not contain nova/bootstrap.py"
  rm -rf "$REPO_DIR"
  mv "$EXTRACTED_DIR" "$REPO_DIR"
  log "Repository staged in $REPO_DIR"
}

resolve_bootstrap() {
  BOOTSTRAP_PATH="$REPO_DIR/nova/bootstrap.py"
  [ -f "$BOOTSTRAP_PATH" ] || die "Could not find $BOOTSTRAP_PATH"
}

install_runtime() {
  PYTHON_BIN="$(detect_python)" || die "Python is not available"
  log "Bootstrapping isolated runtime"
  (
    cd "$REPO_DIR"
    NOVA_BOOTSTRAP_EMBEDDED=1 "$PYTHON_BIN" -m nova.bootstrap install \
      --repo "$REPO_DIR" \
      --bin-dir "$BIN_DIR" \
      --home-dir "$HOME" \
      --python-bin "$PYTHON_BIN"
  ) || die "Failed to bootstrap the isolated runtime"
  [ -x "$NOVA_CMD" ] || die "Failed to resolve the installed nova wrapper"
  log "CLI wrapper created"
}

fresh_shell_resolve_nova() {
  if command -v bash >/dev/null 2>&1; then
    env HOME="$HOME" PATH="$PATH" bash -lc 'command -v nova' 2>/dev/null | head -n 1
    return
  fi
  env HOME="$HOME" PATH="$PATH" sh -lc 'command -v nova' 2>/dev/null | head -n 1
}

validate_nova() {
  log "Validating nova"
  "$NOVA_CMD" help >/dev/null 2>&1 || die "Installed nova wrapper failed to run"
  RESOLVED_NOVA="$(fresh_shell_resolve_nova)"
  [ "$RESOLVED_NOVA" = "$NOVA_CMD" ] || die "Shell resolves nova to '$RESOLVED_NOVA' instead of '$NOVA_CMD'"
  log "Nova CLI is ready"
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
  validate_nova
  start_nova
  log "Installation complete"
  printf '\nUseful commands:\n'
  printf '  nova\n'
  printf '  nova commands\n'
  printf '  nova help\n'
  printf '  tail -f %s/nova.log\n' "$NOVA_DIR"
}

main "$@"
