[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$EnvFile = Join-Path $ProjectRoot ".env"
$DataDir = Join-Path $ProjectRoot "data"
$PidFile = Join-Path $DataDir "kavach.pid"
$StdoutLog = Join-Path $DataDir "server.log"
$StderrLog = Join-Path $DataDir "server-error.log"

if (!(Test-Path -LiteralPath $Python)) {
    throw "Project virtual environment not found: $Python"
}
if (!(Test-Path -LiteralPath $EnvFile)) {
    throw ".env not found. Configure KAVACH before starting."
}

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
Set-Location $ProjectRoot

# Load private configuration into this PowerShell process.
foreach ($line in Get-Content -LiteralPath $EnvFile) {
    $trimmed = $line.Trim()
    if (!$trimmed -or $trimmed.StartsWith("#")) { continue }

    $parts = $trimmed -split "=", 2
    if ($parts.Count -ne 2) {
        throw "Invalid .env entry. Check configuration syntax."
    }

    $key = $parts[0].Trim()
    $value = $parts[1].Trim()

    if ($key -notmatch '^[A-Z][A-Z0-9_]*$') {
        throw "Invalid environment variable name in .env."
    }

    [Environment]::SetEnvironmentVariable($key, $value, "Process")
}

if ([string]::IsNullOrWhiteSpace($env:KAVACH_API_TOKEN) -or
    $env:KAVACH_API_TOKEN.Length -lt 40) {
    throw "KAVACH_API_TOKEN is missing or too short."
}
if ([string]::IsNullOrWhiteSpace($env:KAVACH_DB_PATH)) {
    throw "KAVACH_DB_PATH is missing."
}

$allowedHosts = $env:KAVACH_ALLOWED_HOSTS -split ","
if ($allowedHosts -notcontains "127.0.0.1" -or
    $allowedHosts -notcontains "localhost") {
    throw "Local allowed-host configuration is incomplete."
}

# Refuse to start if this port already has a listener.
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen `
    -ErrorAction SilentlyContinue
if ($listener) {
    throw "Port $Port is already in use. Check whether KAVACH is already running."
}

# Initialize and verify the configured SQLite database.
$dbParent = Split-Path -Parent $env:KAVACH_DB_PATH
New-Item -ItemType Directory -Force -Path $dbParent | Out-Null

& $Python -c "from kavach.audit import init_db; init_db()"
if ($LASTEXITCODE -ne 0) {
    throw "SQLite initialization failed. Check the configured database path."
}

# Remove a stale PID file only when its process no longer exists.
if (Test-Path -LiteralPath $PidFile) {
    $oldPidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
    $oldPid = 0

    if ([int]::TryParse($oldPidText, [ref]$oldPid)) {
        $oldProcess = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($oldProcess) {
            throw "A process with the previous KAVACH PID is still running. Inspect it before starting another server."
        }
    }

    Remove-Item -LiteralPath $PidFile -Force
}

$arguments = "-m uvicorn app:app --host 127.0.0.1 --port $Port"

$server = Start-Process `
    -FilePath $Python `
    -ArgumentList $arguments `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $PidFile -Value $server.Id -Encoding ascii

$dashboardUrl = "http://127.0.0.1:$Port/"
$healthUrl = "http://127.0.0.1:$Port/api/health"
$ready = $false

for ($attempt = 1; $attempt -le 40; $attempt++) {
    if (!(Get-Process -Id $server.Id -ErrorAction SilentlyContinue)) {
        break
    }

    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($health.status -eq "ok") {
            $ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 1
    }
}

if (!$ready) {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue

    Write-Host "KAVACH failed to become healthy." -ForegroundColor Red
    Write-Host "Recent server errors:"
    if (Test-Path $StderrLog) {
        Get-Content $StderrLog -Tail 30
    }
    throw "Startup failed. Review data\server.log and data\server-error.log."
}

Write-Host ""
Write-Host "KAVACH started successfully." -ForegroundColor Green
Write-Host "Backend health: OK"
Write-Host "Dashboard: $dashboardUrl"
try {
    Set-Clipboard -Value $env:KAVACH_API_TOKEN
    Write-Host "API token copied to clipboard (value hidden)."
    Write-Host "Paste it into the dashboard prompt using Ctrl+V."
}
catch {
    Write-Warning "Clipboard copy unavailable. Dashboard will still request the configured token."
}
Write-Host "Database: configured and initialized"
Write-Host "Server PID: $($server.Id)"
Write-Host ""
Write-Host "Use tools\stop_kavach.ps1 to stop the server."

$ChromePath = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe"

if (!(Test-Path $ChromePath)) {
    $ChromePath = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}

if (!(Test-Path $ChromePath)) {
    $ChromePath = "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
}

if (Test-Path $ChromePath) {
    Start-Process -FilePath $ChromePath -ArgumentList $dashboardUrl
    Write-Host "Google Chrome launch requested."
}
else {
    Write-Warning "Chrome not found. Opening the default browser."
    Start-Process $dashboardUrl
}
