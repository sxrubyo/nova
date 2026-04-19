# Nova OS — Windows installer
# irm https://raw.githubusercontent.com/sxrubyo/nova-os/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

$RepoZipUrl = "https://github.com/sxrubyo/nova-os/archive/refs/heads/main.zip"
$NovaHome = Join-Path $env:USERPROFILE ".nova"
$RepoDir = Join-Path $NovaHome "repo"
$BinDir = Join-Path $NovaHome "bin"
$WrapperCmd = Join-Path $BinDir "nova.cmd"

function Write-Banner {
    Write-Host "╭──────────────────────────────────────────────────────────────╮" -ForegroundColor Blue
    Write-Host "│  .      *        .       NOVA OS // launch vector          │" -ForegroundColor Blue
    Write-Host "│     adaptive runtime bootstrap for governed operators      │" -ForegroundColor Blue
    Write-Host "│  repos • terminals • toolchains • policy • live agents     │" -ForegroundColor Blue
    Write-Host "╰──────────────────────────────────────────────────────────────╯" -ForegroundColor Blue
}

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  OK  $Message" -ForegroundColor Green
}

function Fail([string]$Message) {
    Write-Host "  ERR $Message" -ForegroundColor Red
    exit 1
}

function Resolve-Python {
    foreach ($candidate in @("py", "python", "python3")) {
        try {
            if ($candidate -eq "py") {
                $version = & py -3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
                if ($LASTEXITCODE -eq 0) { return "py -3" }
            } else {
                $version = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
                if ($LASTEXITCODE -eq 0) { return $candidate }
            }
        } catch {}
    }
    return $null
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)][string]$PythonCommand,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    if ($PythonCommand -eq "py -3") {
        & py -3 @Arguments
    } else {
        & $PythonCommand @Arguments
    }
}

$Python = Resolve-Python
if (-not $Python) {
    Fail "Python 3 was not found. Install Python and retry."
}

$PythonExecutable = if ($Python -eq "py -3") {
    & py -3 -c "import sys; print(sys.executable)"
} else {
    & $Python -c "import sys; print(sys.executable)"
}

Write-Banner
Write-Step "Preparing Nova OS directories"
New-Item -ItemType Directory -Force -Path $NovaHome | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
if (Test-Path $RepoDir) {
    Remove-Item -Recurse -Force $RepoDir
}

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("nova-os-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
$ZipPath = Join-Path $TempRoot "nova-os.zip"

Write-Step "Downloading Nova OS"
Invoke-WebRequest -UseBasicParsing -Uri $RepoZipUrl -OutFile $ZipPath
Write-Ok "Archive downloaded"

Write-Step "Extracting Nova OS"
Expand-Archive -Path $ZipPath -DestinationPath $TempRoot -Force
$Expanded = Join-Path $TempRoot "nova-os-main"
if (-not (Test-Path (Join-Path $Expanded "nova\bootstrap.py"))) {
    Fail "Downloaded archive does not contain nova/bootstrap.py"
}
Move-Item -Force $Expanded $RepoDir
Write-Ok "Repository staged in $RepoDir"

Write-Step "Bootstrapping isolated runtime"
Push-Location $RepoDir
try {
    $env:NOVA_BOOTSTRAP_EMBEDDED = "1"
    Invoke-Python -PythonCommand $Python -Arguments @(
        "-m", "nova.bootstrap",
        "install",
        "--repo", $RepoDir,
        "--bin-dir", $BinDir,
        "--home-dir", $env:USERPROFILE,
        "--python-bin", $PythonExecutable
    )
} finally {
    Remove-Item Env:NOVA_BOOTSTRAP_EMBEDDED -ErrorAction SilentlyContinue
    Pop-Location
}
if (-not (Test-Path $WrapperCmd)) {
    Fail "Expected wrapper not found at $WrapperCmd"
}
Write-Ok "CLI wrapper created"

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $UserPath) { $UserPath = "" }
if (-not ($UserPath -split ";" | Where-Object { $_ -eq $BinDir })) {
    $NewPath = if ([string]::IsNullOrWhiteSpace($UserPath)) { $BinDir } else { "$UserPath;$BinDir" }
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Ok "User PATH updated"
}
$env:Path = "$BinDir;$env:Path"

Write-Step "Validating nova"
& $WrapperCmd help | Out-Null
Write-Ok "Nova CLI is ready"

Write-Host ""
Write-Host "Nova OS installed." -ForegroundColor White
Write-Host "Open a new terminal if PATH changes are not visible yet." -ForegroundColor DarkGray
Write-Host "Commands:" -ForegroundColor White
Write-Host "  nova help" -ForegroundColor Gray
Write-Host "  nova start" -ForegroundColor Gray
