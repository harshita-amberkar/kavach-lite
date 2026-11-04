$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidFile = Join-Path $ProjectRoot "data\kavach.pid"
$ExpectedPython = [IO.Path]::GetFullPath(
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
)

if (!(Test-Path -LiteralPath $PidFile)) {
    Write-Host "No KAVACH PID file found. Nothing to stop."
    exit 0
}

$pidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
$serverPid = 0

if (![int]::TryParse($pidText, [ref]$serverPid)) {
    throw "Invalid PID file. Inspect data\kavach.pid manually."
}

try {
    $processInfo = Get-CimInstance Win32_Process `
        -Filter "ProcessId = $serverPid" `
        -ErrorAction Stop
}
catch {
    throw "Could not query process information for PID $serverPid. The PID file was left unchanged."
}

if ($null -eq $processInfo) {
    Remove-Item -LiteralPath $PidFile -Force
    Write-Host "Stale PID file removed. KAVACH was not running."
    exit 0
}

if ($null -eq $processInfo.ProcessId -or
    [int]$processInfo.ProcessId -ne $serverPid) {
    throw "Process lookup returned a different PID. Not stopping it."
}

if ([string]::IsNullOrWhiteSpace($processInfo.ExecutablePath) -or
    [string]::Compare(
        [IO.Path]::GetFullPath($processInfo.ExecutablePath),
        $ExpectedPython,
        $true
    ) -ne 0) {
    throw "PID does not belong to the KAVACH virtual environment. Not stopping it."
}

if ([string]::IsNullOrWhiteSpace($processInfo.CommandLine) -or
    $processInfo.CommandLine -notmatch '(?i)(?:^|\s)-m\s+uvicorn\s+app:app(?:\s|$)') {
    throw "PID is not the expected KAVACH Uvicorn process. Not stopping it."
}

Stop-Process -Id $serverPid
Wait-Process -Id $serverPid -Timeout 10 -ErrorAction SilentlyContinue

Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
Write-Host "KAVACH server stopped." -ForegroundColor Green
