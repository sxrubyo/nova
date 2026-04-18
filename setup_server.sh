#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Sube y sirve los installers de Nova CLI desde tu AWS
#  Ejecutar en tu servidor: bash setup_server.sh
#  Maintained by Nova Governance
# ═══════════════════════════════════════════════════════════════
set -e

REPO_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
INSTALL_DIR="$REPO_DIR/installers"
NGINX_CONF="/etc/nginx/sites-available/nova-installer"

echo ""
echo "  Setting up Nova CLI installer server..."
echo ""

# Validaciones básicas
if [ "$EUID" -ne 0 ]; then
    echo "  ✗ Debes ejecutar como root (sudo)."
    exit 1
fi

if [ ! -f "$REPO_DIR/install.sh" ] || [ ! -f "$REPO_DIR/install.ps1" ]; then
    echo "  ✗ No se encontraron installers en $REPO_DIR"
    exit 1
fi

# 1. Crear directorio de installers
mkdir -p "$INSTALL_DIR"
echo "  ✓ Directorio: $INSTALL_DIR"

# 2. Copiar los installers
cp "$REPO_DIR/install.sh"    "$INSTALL_DIR/install.sh"
cp "$REPO_DIR/install.ps1"   "$INSTALL_DIR/install.ps1"
chmod 644 "$INSTALL_DIR"/*.sh "$INSTALL_DIR"/*.ps1
echo "  ✓ Installers copiados"

# 3. Config nginx
cat > "$NGINX_CONF" << NGINX
server {
    listen 3005;
    server_name _;
    root $INSTALL_DIR;

    location = /install {
        default_type text/plain;
        try_files /install.sh =404;
    }
    location = /install.ps1 {
        default_type text/plain;
        try_files /install.ps1 =404;
    }
    location = / {
        default_type text/plain;
        return 200 "Nova CLI Installer\n\nLinux/Mac:  curl -sSL http://SERVER_IP:3005/install | bash\nWindows:    irm http://SERVER_IP:3005/install.ps1 | iex\n";
    }
}
NGINX

# 4. Activar nginx config
if [ -f "/etc/nginx/sites-enabled/nova-installer" ]; then
    rm /etc/nginx/sites-enabled/nova-installer
fi
ln -s "$NGINX_CONF" /etc/nginx/sites-enabled/nova-installer

# 5. Test y reload nginx
nginx -t 2>/dev/null && nginx -s reload
echo "  ✓ Nginx configurado y recargado"

# 6. Mostrar URLs
IP=$(curl -s -4 ifconfig.me 2>/dev/null || echo "TU_IP")
echo ""
echo "  ─────────────────────────────────────────────"
echo ""
echo "  Nova CLI instalable desde cualquier terminal:"
echo ""
echo "  Linux/Mac:"
echo "    curl -sSL http://$IP:3005/install | bash"
echo ""
echo "  Windows PowerShell:"
echo "    irm http://$IP:3005/install.ps1 | iex"
echo ""
echo "  GitHub (después de hacer push):"
echo "    curl -sSL https://raw.githubusercontent.com/Nova/nova-os/main/install.sh | bash"
echo "    irm https://raw.githubusercontent.com/Nova/nova-os/main/install.ps1 | iex"
echo ""
