param(
    [string]$SourcePath = "C:\\Code\\wine-analysis",
    [string]$DestinationPath
)

# Determine repo root (parent of the scripts directory)
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $DestinationPath) {
    $DestinationPath = Join-Path $repoRoot "jetbrains-junie"
}

Write-Host "SourcePath: $SourcePath"
Write-Host "DestinationPath: $DestinationPath"

if (-not (Test-Path -Path $SourcePath)) {
    Write-Error "Source path does not exist: $SourcePath"
    exit 1
}

# Ensure destination exists
if (-not (Test-Path -Path $DestinationPath)) {
    New-Item -ItemType Directory -Path $DestinationPath | Out-Null
}

# Using Robocopy for reliable, fast copying with exclusions
# /E : copy subdirectories, including empty ones
# /MT : multi-threaded copy (default 8)
# /R:2 /W:2 : retry and wait settings
# /NFL /NDL : no file/dir list to reduce noise
# /NP : no progress
# /XO : exclude older files (avoid unnecessary overwrites)
# /XD : exclude directories
# /XF : exclude files

$excludeDirs = @(
    ".git", ".hg", ".svn",
    ".venv", "venv", "env",
    "node_modules",
    "dist", "build", "out", "target",
    ".idea", ".vscode",
    "__pycache__",
    ".mypy_cache", ".pytest_cache"
)

$excludeFiles = @(
    "*.pyc", "*.pyo", "Thumbs.db", ".DS_Store"
)

# Build Robocopy arguments
$robocopyArgs = @()
$robocopyArgs += @("$SourcePath", "$DestinationPath")
$robocopyArgs += @("/E", "/MT:16", "/R:2", "/W:2", "/XO", "/NFL", "/NDL", "/NP")
if ($excludeDirs.Count -gt 0) {
    $robocopyArgs += "/XD"
    $robocopyArgs += $excludeDirs
}
if ($excludeFiles.Count -gt 0) {
    $robocopyArgs += "/XF"
    $robocopyArgs += $excludeFiles
}

Write-Host "Running: robocopy " ($robocopyArgs -join ' ')
$LastExitCode = 0
& robocopy @robocopyArgs | Out-Host
$code = $LastExitCode
# Robocopy exit codes: 0,1=success, >1 indicates some issues; treat 0-7 as success per docs
if ($code -le 7) {
    Write-Host "Migration completed with exit code $code (success)."
    exit 0
} else {
    Write-Error "Robocopy returned exit code $code (failure)."
    exit $code
}