#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  NOVA CLI — Instalador
#  curl -sSL https://get.nova-os.sh | bash
# ══════════════════════════════════════════════════════════════════

set -e

NOVA_VERSION="2.0.0"
INSTALL_DIR="/usr/local/bin"
NOVA_DIR="$HOME/.nova"

# Colors
if [ -t 1 ]; then
  B='\033[1m'
  BLUE='\033[38;5;27m'
  CYAN='\033[38;5;39m'
  GREEN='\033[38;5;84m'
  RED='\033[38;5;196m'
  GRAY='\033[38;5;245m'
  DIM='\033[38;5;238m'
  R='\033[0m'
else
  B='' BLUE='' CYAN='' GREEN='' RED='' GRAY='' DIM='' R=''
fi

ok()   { echo -e "  ${GREEN}✓${R} $1"; }
fail() { echo -e "  ${RED}✗${R} $1"; exit 1; }
info() { echo -e "  ${BLUE}◆${R} ${GRAY}$1${R}"; }
step() { echo -e "\n  ${B}${BLUE}$1${R}"; }

# Logo
echo -e ""
echo -e "  ${BLUE}${B}  ██╗███╗  ██╗ ██████╗ ██╗   ██╗ █████╗  ${R}"
echo -e "  ${BLUE}${B}  ████╗ ██╗██║██╔═══██╗██║   ██║██╔══██╗ ${R}"
echo -e "  ${CYAN}${B}  ██╔████╔╝██║██║   ██║██║   ██║███████║ ${R}"
echo -e "  ${CYAN}${B}  ██║╚██╔╝ ██║██║   ██║╚██╗ ██╔╝██╔══██║ ${R}"
echo -e "  ${CYAN}${B}  ██║ ╚═╝  ██║╚██████╔╝ ╚████╔╝ ██║  ██║ ${R}"
echo -e "  ${CYAN}${B}  ╚═╝      ╚═╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝ ${R}"
echo ""
echo -e "  ${GRAY}Intent Operating System CLI — v${NOVA_VERSION}${R}"
echo -e "  ${DIM}$(printf '─%.0s' {1..42})${R}"
echo ""

# ── Verificar Python ─────────────────────────────────────────────
step "Verificando Python..."
if command -v python3 &>/dev/null; then
  PY=$(python3 --version 2>&1)
  ok "Python encontrado: $PY"
  PYTHON="python3"
elif command -v python &>/dev/null; then
  PY=$(python --version 2>&1)
  ok "Python encontrado: $PY"
  PYTHON="python"
else
  fail "Python 3.8+ es requerido. Instálalo en python.org"
fi

# ── Verificar versión mínima ──────────────────────────────────────
PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
  fail "Se requiere Python 3.8+. Tienes $PY_VERSION"
fi
ok "Versión compatible: Python $PY_VERSION"

# ── Crear directorio ~/.nova ──────────────────────────────────────
step "Preparando directorios..."
mkdir -p "$NOVA_DIR"
ok "Directorio creado: $NOVA_DIR"

# ── Descargar nova.py ─────────────────────────────────────────────
step "Instalando Nova CLI..."
NOVA_BIN="$INSTALL_DIR/nova"

# Intentar con curl, luego wget
if command -v curl &>/dev/null; then
  curl -sSL "https://raw.githubusercontent.com/nova-os/nova-cli/main/nova.py" -o "$NOVA_DIR/nova.py" 2>/dev/null || \
    cp "$(dirname "$0")/nova.py" "$NOVA_DIR/nova.py" 2>/dev/null || true
elif command -v wget &>/dev/null; then
  wget -qO "$NOVA_DIR/nova.py" "https://raw.githubusercontent.com/nova-os/nova-cli/main/nova.py" 2>/dev/null || \
    cp "$(dirname "$0")/nova.py" "$NOVA_DIR/nova.py" 2>/dev/null || true
fi

# Si no se pudo descargar, usar el local
if [ ! -f "$NOVA_DIR/nova.py" ]; then
  if [ -f "$(dirname "$0")/nova.py" ]; then
    cp "$(dirname "$0")/nova.py" "$NOVA_DIR/nova.py"
  else
    fail "No se pudo obtener nova.py. Descárgalo manualmente."
  fi
fi

ok "nova.py instalado en $NOVA_DIR/nova.py"

# ── Crear wrapper ejecutable ──────────────────────────────────────
WRAPPER="#!/usr/bin/env bash
exec $PYTHON \"$NOVA_DIR/nova.py\" \"\$@\""

# Intentar instalar en /usr/local/bin (requiere permisos)
if [ -w "$INSTALL_DIR" ]; then
  echo "$WRAPPER" > "$NOVA_BIN"
  chmod +x "$NOVA_BIN"
  ok "Comando 'nova' instalado en $INSTALL_DIR"
elif sudo -n true 2>/dev/null; then
  echo "$WRAPPER" | sudo tee "$NOVA_BIN" > /dev/null
  sudo chmod +x "$NOVA_BIN"
  ok "Comando 'nova' instalado en $INSTALL_DIR (sudo)"
else
  # Fallback: instalar en ~/.local/bin
  LOCAL_BIN="$HOME/.local/bin"
  mkdir -p "$LOCAL_BIN"
  NOVA_BIN="$LOCAL_BIN/nova"
  echo "$WRAPPER" > "$NOVA_BIN"
  chmod +x "$NOVA_BIN"
  ok "Comando 'nova' instalado en $LOCAL_BIN"
  NEEDS_PATH="$LOCAL_BIN"
fi

# ── Verificar instalación ─────────────────────────────────────────
step "Verificando instalación..."
if $PYTHON "$NOVA_DIR/nova.py" --help &>/dev/null; then
  ok "Nova CLI funciona correctamente"
else
  fail "Algo salió mal. Intenta manualmente: python3 $NOVA_DIR/nova.py"
fi

# ── Resumen ───────────────────────────────────────────────────────
echo ""
echo -e "  ${DIM}$(printf '─%.0s' {1..42})${R}"
echo ""
echo -e "  ${GREEN}${B}Nova CLI instalado exitosamente${R}"
echo ""

if [ -n "$NEEDS_PATH" ]; then
  echo -e "  ${BLUE}◆${R} ${GRAY}Agrega esto a tu ~/.bashrc o ~/.zshrc:${R}"
  echo -e "    ${CYAN}export PATH=\"\$PATH:$NEEDS_PATH\"${R}"
  echo ""
  echo -e "    ${GRAY}Luego: source ~/.bashrc${R}"
  echo ""
fi

echo -e "  ${B}Próximos pasos:${R}"
echo ""
echo -e "    ${CYAN}nova init${R}          ${GRAY}# Conecta con tu servidor Nova${R}"
echo -e "    ${CYAN}nova status${R}        ${GRAY}# Verifica que todo funciona${R}"
echo -e "    ${CYAN}nova agent create${R}  ${GRAY}# Crea tu primer agente${R}"
echo ""
echo -e "  ${GRAY}Documentación: github.com/nova-os/nova-cli${R}"
echo ""
