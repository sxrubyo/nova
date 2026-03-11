#!/usr/bin/env bash
# nova CLI — Linux / macOS Installer
# Maintained by @sxrubyo
# curl -sSL https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.sh | bash
set -euo pipefail

NOVA_VERSION="3.1.5"
NOVA_DIR="$HOME/.nova"
NOVA_PY="$NOVA_DIR/nova.py"
NOVA_BIN="$NOVA_DIR/nova"
NOVA_PY_URL="https://raw.githubusercontent.com/sxrubyo/nova-os/main/nova.py"

R='\033[38;5;196m'; G='\033[38;5;84m'; B='\033[38;5;39m'
D='\033[38;5;238m'; W='\033[38;5;255m'; Y='\033[38;5;244m'
BLD='\033[1m'; RST='\033[0m'

clear; echo ""
printf "${BLD}\033[38;5;18m  ███╗   ██╗  ██████╗  ██╗   ██╗  █████╗   ██████╗██╗     ██╗${RST}\n"
printf "${BLD}\033[38;5;20m  ████╗  ██║ ██╔═══██╗ ██║   ██║ ██╔══██╗ ██╔════╝██║     ██║${RST}\n"
printf "${BLD}\033[38;5;21m  ██╔██╗ ██║ ██║   ██║ ██║   ██║ ███████║ ██║     ██║     ██║${RST}\n"
printf "${BLD}\033[38;5;33m  ██║╚██╗██║ ██║   ██║ ╚██╗ ██╔╝ ██╔══██║ ██║     ██║     ██║${RST}\n"
printf "${BLD}\033[38;5;39m  ██║ ╚████║ ╚██████╔╝  ╚████╔╝  ██║  ██║ ╚██████╗███████╗██║${RST}\n"
printf "${BLD}\033[38;5;45m  ╚═╝  ╚═══╝  ╚═════╝    ╚═══╝   ╚═╝  ╚═╝  ╚══════╝╚══════╝╚═╝${RST}\n"
echo ""; printf "  ${Y}Agents that answer for themselves.${RST}\n"
printf "  ${D}──────────────────────────────────────────────────────${RST}\n\n"

ok()   { printf "  ${G}+${RST}  ${W}$1${RST}\n"; }
fail() { printf "  ${R}x${RST}  ${W}$1${RST}\n"; exit 1; }
step() { printf "  ${B}o${RST}  ${Y}$1${RST}\n"; }

printf "  ${W}${BLD}Installing nova CLI $NOVA_VERSION${RST}\n\n"

PYTHON=""
for cmd in python3 python python3.12 python3.11 python3.10 python3.9 python3.8; do
    if command -v "$cmd" &>/dev/null; then
        maj=$($cmd -c "import sys;print(sys.version_info.major)" 2>/dev/null)
        min=$($cmd -c "import sys;print(sys.version_info.minor)" 2>/dev/null)
        ver=$($cmd -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        if [ "$maj" -ge 3 ] && [ "$min" -ge 8 ] 2>/dev/null; then PYTHON="$cmd"; ok "Python $ver"; break; fi
    fi
done
[ -z "$PYTHON" ] && fail "Python 3.8+ not found. Install from https://python.org"

if [ -d "$NOVA_DIR" ]; then
    step "Removing previous installation..."
    rm -rf "$NOVA_DIR"
fi
mkdir -p "$NOVA_DIR"; ok "Directory ready"
step "Fetching nova.py..."

fetch() {
    if command -v curl &>/dev/null; then
        curl -fsSL "$NOVA_PY_URL" -o "$NOVA_PY"
        return $?
    fi
    if command -v wget &>/dev/null; then
        wget -qO "$NOVA_PY" "$NOVA_PY_URL"
        return $?
    fi
    return 1
}

if ! fetch; then
    fail "Failed to download nova.py. Check your network connection."
fi

if ! grep -q "Nova CLI" "$NOVA_PY" 2>/dev/null; then
    fail "Downloaded nova.py looks invalid."
fi

ok "nova.py ready"

printf '#!/usr/bin/env bash\nexec '"$PYTHON"' "'"$NOVA_PY"'" "$@"\n' > "$NOVA_BIN"
chmod +x "$NOVA_BIN"
ok "nova command created"

for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
    if [ -f "$rc" ] && ! grep -q '\.nova' "$rc" 2>/dev/null; then
        echo 'export PATH="$HOME/.nova:$PATH"' >> "$rc"; ok "PATH updated in $rc"; break
    fi
done

export PATH="$HOME/.nova:$PATH"

echo ""; printf "  ${D}──────────────────────────────────────────────────────${RST}\n"
printf "  ${W}nova CLI installed.${RST}\n"
printf "  ${D}──────────────────────────────────────────────────────${RST}\n\n"

exec "$PYTHON" "$NOVA_PY" init
