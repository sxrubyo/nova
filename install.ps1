# nova CLI — Windows Installer
# Maintained by @sxrubyo
# irm https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.ps1 | iex
$ErrorActionPreference = "Stop"
$NOVA_VERSION = "3.1.5"
$NOVA_DIR = "$env:USERPROFILE\.nova"
$NOVA_PY  = "$NOVA_DIR\nova.py"
$NOVA_CMD = "$NOVA_DIR\nova.cmd"
$NOVA_PY_URL = "https://raw.githubusercontent.com/sxrubyo/nova-os/main/nova.py"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host ""
Write-Host "  ███╗   ██╗  ██████╗  ██╗   ██╗  █████╗   ██████╗██╗     ██╗" -ForegroundColor DarkBlue
Write-Host "  ████╗  ██║ ██╔═══██╗ ██║   ██║ ██╔══██╗ ██╔════╝██║     ██║" -ForegroundColor DarkBlue
Write-Host "  ██╔██╗ ██║ ██║   ██║ ██║   ██║ ███████║ ██║     ██║     ██║" -ForegroundColor Blue
Write-Host "  ██║╚██╗██║ ██║   ██║ ╚██╗ ██╔╝ ██╔══██║ ██║     ██║     ██║" -ForegroundColor Cyan
Write-Host "  ██║ ╚████║ ╚██████╔╝  ╚████╔╝  ██║  ██║ ╚██████╗███████╗██║" -ForegroundColor Cyan
Write-Host "  ╚═╝  ╚═══╝  ╚═════╝    ╚═══╝   ╚═╝  ╚═╝  ╚══════╝╚══════╝╚═╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Agents that answer for themselves." -ForegroundColor DarkGray
Write-Host "  ──────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

function ok($m)   { Write-Host "  " -NoNewline; Write-Host "+" -ForegroundColor Green -NoNewline; Write-Host "  $m" -ForegroundColor White }
function fail($m) { Write-Host "  " -NoNewline; Write-Host "x" -ForegroundColor Red   -NoNewline; Write-Host "  $m" -ForegroundColor White; exit 1 }
function step($m) { Write-Host "  " -NoNewline; Write-Host "o" -ForegroundColor Blue  -NoNewline; Write-Host "  $m" -ForegroundColor DarkGray }

Write-Host "  Installing nova CLI $NOVA_VERSION" -ForegroundColor White
Write-Host ""

$PYTHON = $null
foreach ($cmd in @("py","python","python3")) {
    try {
        $maj = [int](& $cmd -c "import sys; print(sys.version_info.major)" 2>$null)
        $min = [int](& $cmd -c "import sys; print(sys.version_info.minor)" 2>$null)
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($maj -ge 3 -and $min -ge 8) { $PYTHON = $cmd; ok "Python $ver"; break }
    } catch {}
}
if (-not $PYTHON) { fail "Python 3.8+ not found. Install from https://python.org" }

if (Test-Path $NOVA_DIR) {
    step "Removing previous installation..."
    Remove-Item -Recurse -Force $NOVA_DIR
}
New-Item -ItemType Directory -Path $NOVA_DIR -Force | Out-Null
ok "Directory ready"
step "Fetching nova.py..."

try {
    Invoke-WebRequest -UseBasicParsing -Uri $NOVA_PY_URL -OutFile $NOVA_PY
} catch {
    fail "Failed to download nova.py. Check your network connection."
}

$raw = Get-Content -Path $NOVA_PY -Raw
if ($raw -notmatch "Nova CLI") {
    fail "Downloaded nova.py looks invalid."
}

ok "nova.py ready"

"@echo off`r`n$PYTHON `"$NOVA_PY`" %*`r`n" | Set-Content -Path $NOVA_CMD -Encoding ASCII
ok "nova command created"

$pathUser = [Environment]::GetEnvironmentVariable("Path", "User")
if ($pathUser -notmatch [regex]::Escape($NOVA_DIR)) {
    [Environment]::SetEnvironmentVariable("Path", "$pathUser;$NOVA_DIR", "User")
    ok "PATH updated"
}

$env:Path = "$env:Path;$NOVA_DIR"

Write-Host ""
Write-Host "  ──────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  nova CLI installed." -ForegroundColor White
Write-Host "  ──────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

& $PYTHON $NOVA_PY init
