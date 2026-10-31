[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path (Join-Path $root 'app.py')) -or -not (Test-Path (Join-Path $root 'eval\run.py'))) {
    throw 'Run this script from the KAVACH project root (the folder containing app.py and eval\run.py).'
}
if (-not (Test-Path $python)) {
    throw 'Project interpreter not found at .venv\Scripts\python.exe.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js is required for extension/dashboard checks but was not found on PATH.'
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git was not found on PATH.'
}

$logRoot = [System.IO.Path]::GetTempPath()
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $logRoot ('KAVACH-preflight-{0}.log' -f $stamp)
$script:results = @()
$script:preflightExitCode = 0
$transcriptStarted = $false

function Invoke-Check {
    param(
        [string]$Name,
        [string]$Executable,
        [string[]]$Arguments
    )

    Write-Host ''
    Write-Host ('=== {0} ===' -f $Name) -ForegroundColor Cyan
    & $Executable @Arguments
    $code = $LASTEXITCODE
    if ($null -eq $code) {
        $code = 0
    }

    $status = 'PASS'
    if ($code -ne 0) {
        $status = 'FAIL'
        $script:preflightExitCode = 1
    }

    $script:results += [pscustomobject]@{
        Check = $Name
        Status = $status
        ExitCode = $code
    }
    Write-Host ('{0}: {1} (exit {2})' -f $status, $Name, $code)
}

try {
    try {
        Start-Transcript -Path $log -Force | Out-Null
        $transcriptStarted = $true
    }
    catch {
        Write-Warning ('Transcript could not start: {0}' -f $_.Exception.Message)
    }

    Invoke-Check 'Python unit tests' $python @('-m', 'unittest', 'discover', '-v')
    Invoke-Check 'Python bytecode compilation' $python @('-m', 'compileall', '-q', 'app.py', 'kavach', 'tests', 'eval')
    Invoke-Check 'Blind evaluation validator self-tests' $python @('tools/test_validate_blind_gold.py')
    Invoke-Check 'Extension policy and privacy tests' 'node' @('extension/tests/policy_and_privacy.js')
    Invoke-Check 'Extension/Python detector parity' 'node' @('extension/tests/parity.js')
    Invoke-Check 'Dashboard JavaScript syntax' 'node' @('--check', 'static/app.js')
    Invoke-Check 'Extension content script syntax' 'node' @('--check', 'extension/content.js')
    Invoke-Check 'Extension detector syntax' 'node' @('--check', 'extension/detector.js')
    Invoke-Check 'Extension options syntax' 'node' @('--check', 'extension/options.js')
    Invoke-Check 'Extension manifest JSON' $python @('-m', 'json.tool', 'extension/manifest.json')
    Invoke-Check 'Git whitespace check' 'git' @('diff', '--check')

    Write-Host ''
    Write-Host '=== FINAL GIT STATE ===' -ForegroundColor Cyan
    git status --short
    git log -1 --oneline

    Write-Host ''
    Write-Host '=== PREFLIGHT SUMMARY ===' -ForegroundColor Cyan
    $script:results | Format-Table -AutoSize

    if ($script:preflightExitCode -eq 0) {
        Write-Host ('All recorded preflight checks passed. Log: {0}' -f $log) -ForegroundColor Green
    }
    else {
        Write-Host ('One or more preflight checks failed. Review the output and log: {0}' -f $log) -ForegroundColor Red
    }
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}

if ($script:preflightExitCode -ne 0) {
    exit 1
}
