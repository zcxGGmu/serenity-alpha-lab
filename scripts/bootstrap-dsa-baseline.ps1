[CmdletBinding()]
param(
    [string]$BaselineTag = "upstream/dsa-v3.26.1",
    [string]$ExpectedSha = "e8a9ca7742e8cb2498c8f491dd76d239b3064e1a",
    [string]$WorktreePath = ".worktrees/dsa-v3.26.1",
    [string]$CacheRoot = ".cache/dsa-p0",
    [string]$PythonExecutable = "python",
    [int]$InstallRetries = 3,
    [switch]$InstallPython,
    [switch]$InstallCiTools,
    [switch]$InstallWeb,
    [switch]$InstallDesktop,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $Name"
    }
}

function Invoke-Step {
    param(
        [string]$Title,
        [scriptblock]$Script
    )
    Write-Host "==> $Title"
    & $Script
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [int]$Retries = 1
    )
    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        & $FilePath @Arguments
        if ($LASTEXITCODE -eq 0) {
            return
        }
        if ($attempt -eq $Retries) {
            throw "$FilePath failed with exit code $LASTEXITCODE after $attempt attempt(s): $($Arguments -join ' ')"
        }
        Write-Warning "$FilePath failed with exit code $LASTEXITCODE; retrying attempt $($attempt + 1)/$Retries..."
        Start-Sleep -Seconds 15
    }
}

Require-Command git

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$baselineSha = (git rev-parse $BaselineTag).Trim()
if ($baselineSha -ne $ExpectedSha) {
    throw "Baseline tag $BaselineTag resolves to $baselineSha, expected $ExpectedSha"
}

$absoluteWorktree = Join-Path $repoRoot $WorktreePath
$absoluteCache = Join-Path $repoRoot $CacheRoot

if ($ValidateOnly) {
    Write-Host "Baseline tag OK: $BaselineTag -> $baselineSha"
    if (Test-Path $absoluteWorktree) {
        $worktreeSha = (git -C $absoluteWorktree rev-parse HEAD).Trim()
        Write-Host "Existing worktree HEAD: $worktreeSha"
    }
    exit 0
}

Invoke-Step "materialize baseline worktree" {
    if (Test-Path $absoluteWorktree) {
        $worktreeSha = (git -C $absoluteWorktree rev-parse HEAD).Trim()
        if ($worktreeSha -ne $ExpectedSha) {
            throw "Worktree $absoluteWorktree is at $worktreeSha, expected $ExpectedSha"
        }
        Write-Host "Worktree already present at expected SHA."
    } else {
        New-Item -ItemType Directory -Force -Path (Split-Path $absoluteWorktree -Parent) | Out-Null
        Invoke-Native "git" @("worktree", "add", "--detach", $absoluteWorktree, $BaselineTag)
    }
}

Invoke-Step "prepare local env file" {
    $envPath = Join-Path $absoluteWorktree ".env"
    $envExamplePath = Join-Path $absoluteWorktree ".env.example"
    if (-not (Test-Path $envPath) -and (Test-Path $envExamplePath)) {
        Copy-Item $envExamplePath $envPath
        Write-Host "Created $envPath from .env.example. Fill secrets manually before real provider runs."
    } else {
        Write-Host "No env file change needed."
    }
}

if ($InstallPython -or $InstallCiTools) {
    Require-Command $PythonExecutable
    Invoke-Step "create Python virtualenv" {
        New-Item -ItemType Directory -Force -Path $absoluteCache | Out-Null
        $venvPath = Join-Path $absoluteCache "venv"
        if (-not (Test-Path $venvPath)) {
            Invoke-Native $PythonExecutable @("-m", "venv", $venvPath)
        }
        $pythonInVenv = Join-Path $venvPath "Scripts/python.exe"
        $env:PIP_CACHE_DIR = Join-Path $absoluteCache "pip"
        Invoke-Native $pythonInVenv @("-m", "pip", "install", "--upgrade", "pip") -Retries $InstallRetries
        if ($InstallPython) {
            Invoke-Native $pythonInVenv @("-m", "pip", "install", "-r", (Join-Path $absoluteWorktree "requirements.txt")) -Retries $InstallRetries
        }
        if ($InstallCiTools) {
            Invoke-Native $pythonInVenv @("-m", "pip", "install", "-r", (Join-Path $absoluteWorktree ".github/requirements-ci.txt")) -Retries $InstallRetries
        }
    }
}

if ($InstallWeb) {
    Require-Command npm
    Invoke-Step "install DSA web dependencies" {
        $env:npm_config_cache = Join-Path $absoluteCache "npm-web"
        Push-Location (Join-Path $absoluteWorktree "apps/dsa-web")
        try {
            Invoke-Native "npm" @("ci") -Retries $InstallRetries
        } finally {
            Pop-Location
        }
    }
}

if ($InstallDesktop) {
    Require-Command npm
    Invoke-Step "install DSA desktop dependencies" {
        $env:npm_config_cache = Join-Path $absoluteCache "npm-desktop"
        Push-Location (Join-Path $absoluteWorktree "apps/dsa-desktop")
        try {
            Invoke-Native "npm" @("ci") -Retries $InstallRetries
        } finally {
            Pop-Location
        }
    }
}

Write-Host "DSA baseline bootstrap complete."
Write-Host "Worktree: $absoluteWorktree"
Write-Host "Cache: $absoluteCache"
