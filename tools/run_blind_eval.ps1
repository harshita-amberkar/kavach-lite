[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$GoldFile,
    [ValidateSet(3,4)][int]$Participants = 3
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Get-Location).Path).TrimEnd('\')
$python = Join-Path $root '.venv\Scripts\python.exe'
$validator = Join-Path $root 'tools\validate_blind_gold.py'

if (-not (Test-Path (Join-Path $root 'app.py')) -or -not (Test-Path (Join-Path $root 'eval\run.py'))) {
    throw 'Run this script from the KAVACH project root.'
}
if (-not (Test-Path $python)) { throw 'Project interpreter not found.' }
if (-not (Test-Path $validator)) { throw 'Copy this pack into the project root so tools\validate_blind_gold.py exists.' }
if (-not (Test-Path -LiteralPath $GoldFile -PathType Leaf)) { throw "Gold file not found: $GoldFile" }
$resolvedGold = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $GoldFile).Path)
$repoPrefix = $root + '\'
if ($resolvedGold.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Keep gold_hidden.txt outside the Git repository so it is not accidentally committed or exposed.'
}

$gitTopOutput = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw 'Could not identify the Git repository root.' }
$gitTop = [System.IO.Path]::GetFullPath(($gitTopOutput | Out-String).Trim()).TrimEnd('\')
if (-not [string]::Equals($gitTop, $root, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Current directory must be the Git repository root: $gitTop"
}
$gitStatus = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'Could not read Git status.' }
if ($gitStatus) { throw 'Git working tree is not clean. Freeze and commit detector changes before the blind run.' }

# Keep the one-time lock and all prompt-bearing reports outside the Git repository.
$externalDir = Split-Path -Parent $resolvedGold
$lockDir = Join-Path $externalDir 'blind_evaluation_locked'
if (Test-Path $lockDir) {
    throw "A blind-evaluation lock already exists: $lockDir. Do not rerun or tune against this dataset. Preserve the first result."
}

Write-Host '=== Validate format; detector is NOT run during this step ===' -ForegroundColor Cyan
& $python $validator $resolvedGold --participants $Participants
if ($LASTEXITCODE -ne 0) { throw 'Blind gold file validation failed. No evaluation was run.' }

New-Item -ItemType Directory -Force -Path $lockDir | Out-Null
$hash = (Get-FileHash -LiteralPath $resolvedGold -Algorithm SHA256).Hash.ToLowerInvariant()
$commitOutput = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Could not record the frozen Git commit.' }
$commit = ($commitOutput | Out-String).Trim()
$manifestPath = Join-Path $lockDir 'manifest.json'
$manifest = [ordered]@{
    dataset_path = $resolvedGold
    dataset_sha256 = $hash
    participants = $Participants
    frozen_git_commit = $commit
    started_at_local = (Get-Date).ToString('o')
    evaluation = 'KAVACH eval.run --gold-file; one-time synthetic holdout run'
    status = 'started'
    errors_file_contents = 'metadata, entity types and character offsets only; no raw prompt text or entity values'
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Set-Content -LiteralPath (Join-Path $lockDir 'dataset.sha256') -Value "$hash  gold_hidden.txt" -Encoding ASCII

# eval.run writes fixed filenames in results/. Preserve and restore them so this
# run cannot silently overwrite existing benchmark reports in the Git checkout.
$resultsDir = Join-Path $root 'results'
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null
$previousDir = Join-Path $lockDir 'previous_results'
New-Item -ItemType Directory -Force -Path $previousDir | Out-Null
$names = @('report.md','report.json','errors.jsonl')
$hadPrevious = @{}
foreach ($name in $names) {
    $source = Join-Path $resultsDir $name
    $hadPrevious[$name] = Test-Path $source
    if ($hadPrevious[$name]) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $previousDir $name)
    }
}
$manifest.previous_results_existed = $hadPrevious
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

$exitCode = 1
$failure = $null
try {
    foreach ($name in $names) {
        $stale = Join-Path $resultsDir $name
        if (Test-Path $stale) { Remove-Item -LiteralPath $stale -Force }
    }
    Write-Host "`n=== ONE-TIME BLIND EVALUATION ===" -ForegroundColor Cyan
    & $python -m eval.run --gold-file $resolvedGold
    $exitCode = $LASTEXITCODE
    foreach ($name in $names) {
        $source = Join-Path $resultsDir $name
        if (Test-Path $source) {
            Copy-Item -LiteralPath $source -Destination (Join-Path $lockDir $name) -Force
        }
    }
    if ($exitCode -ne 0) {
        throw "Evaluation process failed with exit code $exitCode."
    }
    foreach ($name in $names) {
        if (-not (Test-Path (Join-Path $lockDir $name))) {
            throw "Expected evaluator output missing: $name"
        }
    }
    $manifest.status = 'completed'
}
catch {
    $failure = $_.Exception.Message
    $manifest.status = 'failed_after_start; do not rerun this dataset'
    $manifest.failure = $failure
}
finally {
    foreach ($name in $names) {
        $source = Join-Path $resultsDir $name
        if ($hadPrevious[$name]) {
            Copy-Item -LiteralPath (Join-Path $previousDir $name) -Destination $source -Force
        } elseif (Test-Path $source) {
            Remove-Item -LiteralPath $source -Force
        }
    }
    $manifest.finished_at_local = (Get-Date).ToString('o')
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}

if ($failure) {
    throw "$failure Preserve $lockDir and investigate without changing the detector or rerunning this set."
}
Write-Host "`nBlind evaluation archived outside Git at: $lockDir" -ForegroundColor Green
Write-Host 'Do not tune the detector against this dataset. Any future validation requires a new independently authored holdout.' -ForegroundColor Yellow
Write-Host 'Note: errors.jsonl contains error metadata and character offsets, not raw prompt text or entity values. Keep the synthetic dataset and archive access-controlled.' -ForegroundColor Yellow
