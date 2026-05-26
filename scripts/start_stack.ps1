# Auto-select the Ollama model based on detected GPU VRAM, then bring up
# the full Paedia / EduRAG Docker stack on Windows / PowerShell.
#
# Decision rule
#   VRAM >= VramThresholdGb (default 12)  -> HighVramModel  (qwen3:14b)
#   VRAM <  VramThresholdGb OR no GPU     -> LowVramModel   (llama3.2)
#
# The 8-12 GB band falls into LowVramModel because qwen3:14b's ~10 GB
# working set partially offloads to RAM on smaller GPUs and loses the
# speedup the model is chosen for. See docs/sprint5_implementation_summary.md
# §5 for the rationale.

[CmdletBinding()]
param(
    [string]$HighVramModel   = "qwen3:14b",
    [string]$LowVramModel    = "llama3.2",
    [int]   $VramThresholdGb = 12,
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot   = Split-Path -Parent $ScriptDir
$EnvFile    = Join-Path $RepoRoot ".env"
$EnvExample = Join-Path $RepoRoot ".env.example"
$Utf8NoBom  = [System.Text.UTF8Encoding]::new($false)

function Get-VramGb {
    $cmd = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { return 0 }
    try {
        $raw = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null
        $first = ($raw | Select-Object -First 1)
        if ($null -eq $first) { return 0 }
        $mb = [int]($first.ToString().Trim())
        return [int][Math]::Floor(($mb + 512) / 1024)
    } catch {
        return 0
    }
}

function Write-EnvFileLines {
    param([string[]]$Lines)
    $content = ($Lines -join [Environment]::NewLine) + [Environment]::NewLine
    [System.IO.File]::WriteAllText($EnvFile, $content, $Utf8NoBom)
}

function Set-EnvVar {
    param([string]$Key, [string]$Value)
    if (Test-Path $EnvFile) {
        $lines = [System.IO.File]::ReadAllLines($EnvFile)
        $pattern = "^$([regex]::Escape($Key))="
        if ($lines -match $pattern) {
            $lines = $lines | ForEach-Object {
                if ($_ -match $pattern) { "$Key=$Value" } else { $_ }
            }
            Write-EnvFileLines $lines
        } else {
            Write-EnvFileLines ($lines + "$Key=$Value")
        }
    } else {
        Write-EnvFileLines @("$Key=$Value")
    }
}

$vramGb = Get-VramGb

if ($vramGb -ge $VramThresholdGb) {
    $chosen        = $HighVramModel
    $reason        = "VRAM $vramGb GB >= $VramThresholdGb GB threshold"
    $useGpuOverlay = $true
} elseif ($vramGb -gt 0) {
    $chosen        = $LowVramModel
    $reason        = "VRAM $vramGb GB < $VramThresholdGb GB threshold (partial offload would defeat speedup)"
    $useGpuOverlay = $true
} else {
    $chosen        = $LowVramModel
    $reason        = "no NVIDIA GPU detected (CPU-only path)"
    $useGpuOverlay = $false
}

Write-Host "[start_stack] Detected GPU memory : $vramGb GB"
Write-Host "[start_stack] Selected LLM model  : $chosen"
Write-Host "[start_stack] Reason              : $reason"

if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "[start_stack] Created .env from .env.example"
}

Set-EnvVar -Key "DEFAULT_OLLAMA_MODEL" -Value $chosen
Write-Host "[start_stack] Wrote DEFAULT_OLLAMA_MODEL=$chosen to .env"

$composeArgs = @("-f", (Join-Path $RepoRoot "docker-compose.yml"))
if ($useGpuOverlay) {
    $composeArgs += @("-f", (Join-Path $RepoRoot "docker-compose.gpu.yml"))
    Write-Host "[start_stack] Including docker-compose.gpu.yml overlay"
}

Set-Location $RepoRoot
Write-Host "[start_stack] docker compose $($composeArgs -join ' ') up -d --build"
& docker compose @composeArgs up -d --build

Write-Host "[start_stack] Waiting for Ollama at http://localhost:11434/api/tags ..."
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2
        $ok = $true
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $ok) {
    Write-Warning "Ollama did not become ready in 60s; continuing anyway."
}

if (-not $SkipPull) {
    Write-Host "[start_stack] Pulling $chosen into Ollama (cached if already present)..."
    & docker compose @composeArgs exec -T ollama ollama pull $chosen
} else {
    Write-Host "[start_stack] -SkipPull set, skipping ollama pull"
}

Write-Host ""
Write-Host "[start_stack] Done."
Write-Host "  UI    : http://localhost:8501"
Write-Host "  API   : http://localhost:5000/api/health"
Write-Host "  Model : $chosen  (selected on $vramGb GB VRAM)"
